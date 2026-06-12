# dateParser.py
# NVDA Global Plugin: Date Parser

import globalPluginHandler
from scriptHandler import script
import ui
import addonHandler
from datetime import datetime, timedelta, date
import wx
import gui
import re
import calendar
import os

addonHandler.initTranslation()

# Canonical weekday numbers (Python: Monday=0)
_WEEKDAY_CANON = {
	"monday": 0,
	"tuesday": 1,
	"wednesday": 2,
	"thursday": 3,
	"friday": 4,
	"saturday": 5,
	"sunday": 6,
}

# Accept lots of abbreviations / variants.
WEEKDAY_ALIASES = {
	"mon": "monday",
	"monday": "monday",
	"tue": "tuesday",
	"tues": "tuesday",
	"tuesday": "tuesday",
	"wed": "wednesday",
	"weds": "wednesday",
	"wednesday": "wednesday",
	"thu": "thursday",
	"thur": "thursday",
	"thurs": "thursday",
	"thursday": "thursday",
	"fri": "friday",
	"friday": "friday",
	"sat": "saturday",
	"saturday": "saturday",
	"sun": "sunday",
	"sunday": "sunday",
}

# Month names (short + long). Keys are normalized to lowercase, no trailing dot.
MONTH_ALIASES = {
	"jan": 1, "january": 1,
	"feb": 2, "february": 2,
	"mar": 3, "march": 3,
	"apr": 4, "april": 4,
	"may": 5,
	"jun": 6, "june": 6,
	"jul": 7, "july": 7,
	"aug": 8, "august": 8,
	"sep": 9, "sept": 9, "september": 9,
	"oct": 10, "october": 10,
	"nov": 11, "november": 11,
	"dec": 12, "december": 12,
}

# Basic number words support (extend as you like)
NUM_WORDS = {
	"zero": 0,
	"one": 1,
	"two": 2,
	"three": 3,
	"four": 4,
	"five": 5,
	"six": 6,
	"seven": 7,
	"eight": 8,
	"nine": 9,
	"ten": 10,
	"eleven": 11,
	"twelve": 12,
	"thirteen": 13,
	"fourteen": 14,
	"fifteen": 15,
	"sixteen": 16,
	"seventeen": 17,
	"eighteen": 18,
	"nineteen": 19,
	"twenty": 20,
	"thirty": 30,
	"forty": 40,
	"fifty": 50,
	"sixty": 60,
	"seventy": 70,
	"eighty": 80,
	"ninety": 90,
}

_ORDINAL_SUFFIX_RE = re.compile(r"^(\d+)(st|nd|rd|th)$", re.IGNORECASE)

# Friendly month-name date formats:
# - DMY: "13 Apr 2026", "5 Mar", "5 March 2026", "13-Apr-2026", "13/Apr/2026"
# - MDY: "Mar 5", "March 5 2026", "Mar-5-2026"
_FRIENDLY_DMY_OPTIONAL_YEAR_RE = re.compile(
	r"^\s*(\d{1,2})(?:st|nd|rd|th)?\s*[-/ ]\s*([a-zA-Z]+)\.?\s*(?:[-/ ]\s*(\d{2,4}))?\s*$"
)
_FRIENDLY_MDY_OPTIONAL_YEAR_RE = re.compile(
	r"^\s*([a-zA-Z]+)\.?\s*[-/ ]\s*(\d{1,2})(?:st|nd|rd|th)?\s*(?:[-/ ,]\s*(\d{2,4}))?\s*$"
)

_NUMERIC_DATE_RE = re.compile(
	r"(?<!\d)(\d{1,4})\s*([./-])\s*(\d{1,2})\s*\2\s*(\d{2,4})"
)
_NUMERIC_DATE_OPTIONAL_YEAR_RE = re.compile(
	r"^\s*(\d{1,2})\s*([./-])\s*(\d{1,2})(?:\s*\2\s*(\d{2,4}))?\s*$"
)
_WEEKDAY_PREFIX_RE = re.compile(
	r"^\s*([a-zA-Z]+)\.?,?\s+(.+?)\s*$"
)
_WEEKDAY_SUFFIX_RE = re.compile(
	r"^\s*(.+?)\s+([a-zA-Z]+)\.?\s*$"
)
_DAY_WEEKDAY_RE = re.compile(
	r"^\s*([+-]?)\s*(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)\.?\s*$"
)
_WEEKDAY_DAY_RE = re.compile(
	r"^\s*([+-]?)\s*([a-zA-Z]+)\.?\s+(\d{1,2})(?:st|nd|rd|th)?\s*$"
)
_COMPACT_COUNTED_WEEKDAY_RE = re.compile(
	r"^\s*([+-]?)(\d+)(?:st|nd|rd|th)?\s*([a-zA-Z]+)\.?\s*(?:(ago|prior|previously|before|back|from now|ahead|later|after))?\s*$"
)
_COUNTED_WEEKDAY_SHORT_RE = re.compile(
	r"^\s*(\d+)(?:st|nd|rd|th)?\s+([a-zA-Z]+)s?\s+(ago|prior|previously|before|back|from now|ahead|later|after)\s*$"
)
_COUNTED_WEEKDAY_PHRASE_RE = re.compile(
	r"^\s*(\d+)(?:st|nd|rd|th)?\s+([a-zA-Z]+)s?\s+(?:from\s+now|ago)\s*$"
)
_NATURAL_RELATIVE_RE = re.compile(
	r"^\s*(?:(in)\s+)?(.+?)\s+(day|days|week|weeks|month|months|year|years)\s*(?:(ago|from now|ahead|later))?\s*$"
)
_BOUNDARY_DATE_RE = re.compile(
	r"^\s*(start|beginning|first|end|last)\s+(?:of\s+)?(?:(this|next|last)\s+)?(month|year)\s*$"
)

# Compact relative units (single or multiple):
# Examples: 5d, -5d, +2w, 6m, 1y, 5y 4m 3w 2d, with optional trailing "ago"/"from now"
_MULTI_COMPACT_REL_RE = re.compile(
	r"^\s*([+-]?\d+\s*[dDwWmMyY]\s*)+(?:ago|from\s+now|ahead|later)?\s*$"
)
_MULTI_COMPACT_REL_TOKEN_RE = re.compile(r"([+-]?\d+)\s*([dDwWmMyY])")


def _parse_int_maybe_words(token: str) -> int:
	token = token.strip().lower()
	m = _ORDINAL_SUFFIX_RE.match(token)
	if m:
		return int(m.group(1))

	if re.fullmatch(r"\d+", token):
		return int(token)

	parts = token.split()
	if len(parts) == 1:
		if parts[0] in NUM_WORDS:
			return NUM_WORDS[parts[0]]
		raise ValueError(_("Unknown number word: %s") % token)

	if len(parts) == 2:
		tens, ones = parts
		if tens in NUM_WORDS and ones in NUM_WORDS and NUM_WORDS[tens] >= 20 and NUM_WORDS[ones] < 10:
			return NUM_WORDS[tens] + NUM_WORDS[ones]

	raise ValueError(_("Unsupported number format: %s") % token)


def _canonicalize_weekday(token: str) -> str:
	token = token.strip().lower()
	if token.endswith("s"):
		token = token[:-1]  # allow plural
	if token in WEEKDAY_ALIASES:
		return WEEKDAY_ALIASES[token]
	raise ValueError(_("Unknown weekday: %s") % token)


def _parse_month_token(token: str) -> int:
	t = token.strip().lower().rstrip(".")
	if t in MONTH_ALIASES:
		return MONTH_ALIASES[t]
	raise ValueError(_("Unknown month: %s") % token)


def _parse_year_token(token: str) -> int:
	year = int(token)
	if year < 100:
		return 2000 + year if year <= 69 else 1900 + year
	return year


def _normalize_input_text(text: str) -> str:
	text = (text or "").strip()
	text = text.replace("\u2013", "-").replace("\u2014", "-").replace("\u2212", "-")
	text = re.sub(r"\s+", " ", text)
	return text.strip()


def _choose_year_for_month_day(today: date, month: int, day: int, year):
	if year is not None:
		return year
	this_year = today.year
	candidate = date(this_year, month, day)
	return this_year if candidate >= today else this_year + 1


def _choose_year_for_month_day_direction(today: date, month: int, day: int, direction: int) -> int:
	year = today.year
	candidate = date(year, month, day)
	if direction < 0:
		return year if candidate <= today else year - 1
	return year if candidate >= today else year + 1


def _last_day_of_month(year: int, month: int) -> int:
	return calendar.monthrange(year, month)[1]


def _add_months(d: date, months: int) -> date:
	y = d.year + (d.month - 1 + months) // 12
	m = (d.month - 1 + months) % 12 + 1
	day = min(d.day, _last_day_of_month(y, m))
	return date(y, m, day)


def _date_with_day_and_weekday(today: date, day: int, weekday: int, direction: int) -> date:
	if day < 1 or day > 31:
		raise ValueError(_("Day must be between 1 and 31."))

	cursor = date(today.year, today.month, 1)
	if direction < 0:
		cursor = _add_months(cursor, -1 if today.day < day else 0)
		for _ in range(240):
			if day <= _last_day_of_month(cursor.year, cursor.month):
				candidate = date(cursor.year, cursor.month, day)
				if candidate <= today and candidate.weekday() == weekday:
					return candidate
			cursor = _add_months(cursor, -1)
	else:
		cursor = _add_months(cursor, 1 if today.day > day else 0)
		for _ in range(240):
			if day <= _last_day_of_month(cursor.year, cursor.month):
				candidate = date(cursor.year, cursor.month, day)
				if candidate >= today and candidate.weekday() == weekday:
					return candidate
			cursor = _add_months(cursor, 1)

	raise ValueError(_("Could not find a matching day and weekday."))


def _parse_boundary_date(today: date, text: str):
	m = _BOUNDARY_DATE_RE.match(text)
	if not m:
		raise ValueError(_("No boundary date found."))

	which, direction, unit = m.groups()
	direction = direction or "this"
	is_start = which in ("start", "beginning", "first")

	if unit == "month":
		offset = 1 if direction == "next" else -1 if direction == "last" else 0
		base = _add_months(date(today.year, today.month, 1), offset)
		target = base if is_start else date(base.year, base.month, _last_day_of_month(base.year, base.month))
	else:
		year = today.year + (1 if direction == "next" else -1 if direction == "last" else 0)
		target = date(year, 1, 1) if is_start else date(year, 12, 31)

	boundary = _("start") if is_start else _("end")
	hint = _("%(boundary)s of %(direction)s %(unit)s") % {
		"boundary": boundary,
		"direction": direction,
		"unit": unit,
	}
	return target, hint


def _diff_years_months_weeks_days(start: date, end: date):
	if end < start:
		start, end = end, start

	years = end.year - start.year
	candidate = _add_months(start, years * 12)
	if candidate > end:
		years -= 1
		candidate = _add_months(start, years * 12)

	months = (end.year - candidate.year) * 12 + (end.month - candidate.month)
	candidate2 = _add_months(candidate, months)
	if candidate2 > end:
		months -= 1
		candidate2 = _add_months(candidate, months)

	remaining_days = (end - candidate2).days
	weeks = remaining_days // 7
	days = remaining_days % 7

	return years, months, weeks, days


def _fmt_unit(n: int, singular: str, plural: str) -> str:
	return f"{n} {singular if n == 1 else plural}"


def _fmt_distance(years: int, months: int, weeks: int, days: int) -> str:
	parts = []
	if years:
		parts.append(_fmt_unit(years, _("year"), _("years")))
	if months:
		parts.append(_fmt_unit(months, _("month"), _("months")))
	if weeks:
		parts.append(_fmt_unit(weeks, _("week"), _("weeks")))
	if days:
		parts.append(_fmt_unit(days, _("day"), _("days")))
	if not parts:
		return _("0 days")
	return ", ".join(parts)


def _distance_between(a: date, b: date) -> str:
	start, end = (a, b) if a <= b else (b, a)
	y, m, w, d = _diff_years_months_weeks_days(start, end)
	return _fmt_distance(y, m, w, d)


def _next_weekday_inclusive(base: date, weekday: int) -> date:
	days_ahead = (weekday - base.weekday() + 7) % 7
	return base + timedelta(days=days_ahead)


def _next_weekday_exclusive(base: date, weekday: int) -> date:
	days_ahead = (weekday - base.weekday() + 7) % 7
	if days_ahead == 0:
		days_ahead = 7
	return base + timedelta(days=days_ahead)


def _prev_weekday_exclusive(base: date, weekday: int) -> date:
	days_back = (base.weekday() - weekday + 7) % 7
	if days_back == 0:
		days_back = 7
	return base - timedelta(days=days_back)


def _nth_weekday_from_today(today: date, weekday: int, n: int) -> date:
	if n <= 0:
		raise ValueError(_("Count must be positive."))
	first = _next_weekday_exclusive(today, weekday)
	return first + timedelta(days=7 * (n - 1))


def _nth_weekday_ago(today: date, weekday: int, n: int) -> date:
	if n <= 0:
		raise ValueError(_("Count must be positive."))
	first = _prev_weekday_exclusive(today, weekday)
	return first - timedelta(days=7 * (n - 1))


def _parse_counted_weekday(today: date, count_s: str, weekday_s: str, direction_s: str, sign_s: str = ""):
	n = int(count_s)
	if n <= 0:
		raise ValueError(_("Count must be positive."))
	day_name = _canonicalize_weekday(weekday_s)
	weekday = _WEEKDAY_CANON[day_name]
	day_label = day_name.capitalize() if n == 1 else day_name.capitalize() + "s"
	direction_s = (direction_s or "").lower()
	if sign_s == "-" or direction_s in ("ago", "prior", "previously", "before", "back"):
		target = _nth_weekday_ago(today, weekday, n)
		hint = _("%(n)d %(day)s ago") % {"n": n, "day": day_label}
	else:
		target = _nth_weekday_from_today(today, weekday, n)
		hint = _("%(n)d %(day)s from now") % {"n": n, "day": day_label}
	return target, hint


def _apply_compact_relative(today: date, text: str):
	norm = re.sub(r"\s+", " ", text.strip().lower())

	direction_sign = None
	m_dir = re.search(r"\s+(ago|from now|ahead|later)\s*$", norm)
	if m_dir:
		direction = m_dir.group(1)
		direction_sign = -1 if direction == "ago" else 1
		norm = re.sub(r"\s+(ago|from now|ahead|later)\s*$", "", norm).strip()

	tokens = _MULTI_COMPACT_REL_TOKEN_RE.findall(norm)
	if not tokens:
		raise ValueError(_("No relative tokens found."))

	years = months = weeks = days = 0
	for n_s, u in tokens:
		raw = int(n_s)
		if n_s.startswith(("+", "-")):
			n = raw
		elif direction_sign is not None:
			n = raw * direction_sign
		else:
			n = raw
		u = u.lower()
		if u == "y":
			years += n
		elif u == "m":
			months += n
		elif u == "w":
			weeks += n
		elif u == "d":
			days += n

	target = today
	total_months = (years * 12) + months
	if total_months:
		target = _add_months(target, total_months)
	if weeks or days:
		target = target + timedelta(days=(weeks * 7 + days))

	parts = []
	if years: parts.append(f"{years:+d}y")
	if months: parts.append(f"{months:+d}m")
	if weeks: parts.append(f"{weeks:+d}w")
	if days: parts.append(f"{days:+d}d")
	hint = " ".join(parts) if parts else ""
	explicit_signs = [n_s[0] for n_s, u in tokens if n_s.startswith(("+", "-"))]
	has_explicit_positive = "+" in explicit_signs
	has_explicit_negative = "-" in explicit_signs
	has_mixed_explicit_signs = has_explicit_positive and has_explicit_negative
	total_months = (years * 12) + months
	total_days = (weeks * 7) + days
	net_is_negative = total_months < 0 or (total_months == 0 and total_days < 0)

	if has_mixed_explicit_signs:
		hint = _("mixed signed offset: ") + hint
	elif direction_sign is not None and all(not n_s.startswith(("+", "-")) for n_s, u in tokens):
		hint = hint.replace("+", "", 1) if hint.startswith("+") else hint
		hint = hint.replace("+", "")
		hint = hint.replace("-", "")
		hint = hint + (" ago" if direction_sign < 0 else " from now")
	elif net_is_negative:
		hint = hint.replace("+", "")
		hint = hint.replace("-", "")
		hint = hint + " ago"
	else:
		hint = hint.replace("+", "")
		hint = hint + " from now"

	# Only suppress Day offset line when user already expressed a days-only offset.
	total_days_already_explicit = (years == 0 and months == 0 and weeks == 0 and days != 0)
	return target, hint.strip(), total_days_already_explicit


def _apply_natural_relative(today: date, text: str):
	norm = re.sub(r"\s+", " ", text.strip().lower())

	shortcuts = {
		"next day": (1, "day"),
		"last day": (-1, "day"),
		"next week": (1, "week"),
		"last week": (-1, "week"),
		"next month": (1, "month"),
		"last month": (-1, "month"),
		"next year": (1, "year"),
		"last year": (-1, "year"),
	}
	if norm in shortcuts:
		amount, unit = shortcuts[norm]
	else:
		m = _NATURAL_RELATIVE_RE.match(norm)
		if not m:
			raise ValueError(_("No natural relative date found."))
		in_prefix, n_token, unit, direction_word = m.groups()
		amount = _parse_int_maybe_words(n_token.replace("-", " "))
		if amount < 0:
			raise ValueError(_("Count must be positive."))
		unit = unit.rstrip("s")
		if direction_word == "ago":
			amount = -amount
		elif in_prefix or direction_word in ("from now", "ahead", "later") or direction_word is None:
			amount = amount
		else:
			raise ValueError(_("Unsupported relative date direction."))

	if unit == "day":
		target = today + timedelta(days=amount)
	elif unit == "week":
		target = today + timedelta(days=amount * 7)
	elif unit == "month":
		target = _add_months(today, amount)
	elif unit == "year":
		target = _add_months(today, amount * 12)
	else:
		raise ValueError(_("Unsupported relative unit."))

	label_amount = abs(amount)
	label_unit = _fmt_unit(label_amount, unit, unit + "s")
	if amount == 0:
		hint = _("today")
	elif amount < 0:
		hint = _("%s ago") % label_unit
	else:
		hint = _("in %s") % label_unit
	return target, hint, unit == "day"


class ResultDialog(wx.Dialog):
	def __init__(self, parent, title, messageText):
		super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)

		panel = wx.Panel(self)
		vbox = wx.BoxSizer(wx.VERTICAL)

		self.textCtrl = wx.TextCtrl(
			panel,
			value=messageText,
			style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2,
		)
		vbox.Add(self.textCtrl, 1, wx.EXPAND | wx.ALL, 10)

		btnSizer = wx.StdDialogButtonSizer()
		okBtn = wx.Button(panel, wx.ID_OK, label=_("OK"))
		btnSizer.AddButton(okBtn)
		btnSizer.Realize()
		vbox.Add(btnSizer, 0, wx.ALIGN_RIGHT | wx.ALL, 10)

		panel.SetSizer(vbox)

		self.SetMinSize((520, 260))
		self.CentreOnParent()

		self.textCtrl.SetFocus()
		self.textCtrl.SelectAll()

		self.Bind(wx.EVT_CHAR_HOOK, self._onCharHook)

	def _onCharHook(self, event):
		key = event.GetKeyCode()
		if key == wx.WXK_F1:
			openManual()
			return
		if key in (wx.WXK_ESCAPE, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			self.EndModal(wx.ID_OK)
			return
		event.Skip()


def openManual():
	try:
		addon = addonHandler.getCodeAddon()
		path = os.path.join(addon.path, "doc", "en", "readme.html")
		if os.path.exists(path):
			os.startfile(path)
			return
	except Exception:
		pass
	ui.message(_("Help is not available."))


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = "Date Parser"

	@script(
		description=_("Parse a date expression and show the result"),
		gesture="kb:NVDA+alt+e"
	)
	def script_dateInput(self, gesture):
		wx.CallAfter(self._showInputDialog)

	def _showInputDialog(self):
		text = ""
		try:
			dlg = wx.TextEntryDialog(
				gui.mainFrame,
				_("Enter a date expression. Press F1 for examples and help."),
				_("Date parser")
			)
			dlg.Bind(wx.EVT_CHAR_HOOK, self._onInputCharHook)

			if dlg.ShowModal() != wx.ID_OK:
				dlg.Destroy()
				return

			text = (dlg.GetValue() or "").strip()
			dlg.Destroy()

			if not text:
				return

			resultText = self._parseDateExpression(text)

			ui.message(resultText)
			self._showResultDialog(resultText)

		except Exception as e:
			msg = (
				_("Could not parse that input.")
				+ "\n\n"
				+ _("Input: ")
				+ (text if text else _("(empty)"))
				+ "\n"
				+ _("Error: ")
				+ str(e)
				+ "\n\n"
				+ _("Press F1 for examples and help.")
			)
			ui.message(_("Error: invalid date expression."))
			self._showResultDialog(msg)

	def _onInputCharHook(self, event):
		if event.GetKeyCode() == wx.WXK_F1:
			openManual()
			return
		event.Skip()

	def _showResultDialog(self, resultText):
		dlg = ResultDialog(gui.mainFrame, _("Date parser result"), resultText)
		dlg.ShowModal()
		dlg.Destroy()

	def _parseDateExpression(self, text):
		today = datetime.now().date()
		original_text = _normalize_input_text(text)
		text = original_text.lower()
		target = None
		human_hint = ""
		total_days_already_explicit = False
		show_calendar_distance = False

		# Weekday token alone: "mon" -> next occurrence (inclusive)
		try:
			day_name = _canonicalize_weekday(text)
			weekday = _WEEKDAY_CANON[day_name]
			target = _next_weekday_inclusive(today, weekday)
			human_hint = _("this %s") % day_name.capitalize() if target == today else _("next %s") % day_name.capitalize()
		except Exception:
			pass

		# Keywords
		if target is None:
			if text == "today":
				target = today
				human_hint = _("today")
			elif text == "tomorrow":
				target = today + timedelta(days=1)
				human_hint = _("tomorrow")
			elif text == "yesterday":
				target = today - timedelta(days=1)
				human_hint = _("yesterday")
			elif text in ("next year", "last year", "next month", "last month", "next week", "last week"):
				target, human_hint, total_days_already_explicit = _apply_natural_relative(today, text)
				show_calendar_distance = True

		# Numeric day offsets: -365, +10, 365
		if target is None and re.fullmatch(r"[+-]?\d+", text):
			offset = int(text)
			target = today + timedelta(days=offset)
			if offset == 0:
				human_hint = _("today")
			elif offset > 0:
				human_hint = _("in %(n)d days") % {"n": offset}
			else:
				human_hint = _("%(n)d days ago") % {"n": abs(offset)}
			total_days_already_explicit = True
			show_calendar_distance = abs(offset) >= 60

		# Compact relative units: 5d, -5d, 2w from now, 1y, 5y 4m 3w 2d
		if target is None and _MULTI_COMPACT_REL_RE.match(text):
			target, human_hint, total_days_already_explicit = _apply_compact_relative(today, text)
			show_calendar_distance = True

		if target is None:
			norm = re.sub(r"\s+", " ", text.strip().lower())

			# Natural relative wording: "in 3 days", "three weeks ago", "a year ago".
			if target is None:
				natural_norm = norm.replace("a ", "one ", 1) if norm.startswith("a ") else norm
				natural_norm = natural_norm.replace("an ", "one ", 1) if natural_norm.startswith("an ") else natural_norm
				try:
					target, human_hint, total_days_already_explicit = _apply_natural_relative(today, natural_norm)
					show_calendar_distance = not total_days_already_explicit
				except Exception:
					pass

			# Boundaries: "end of month", "start of next year".
			if target is None:
				try:
					target, human_hint = _parse_boundary_date(today, norm)
					show_calendar_distance = True
				except Exception:
					pass

			# N weekday(s) from now / ago
			if target is None:
				m_short = _COUNTED_WEEKDAY_SHORT_RE.match(norm)
				m_compact = _COMPACT_COUNTED_WEEKDAY_RE.match(norm)
				if m_short:
					n_s, day_token, direction = m_short.groups()
					target, human_hint = _parse_counted_weekday(today, n_s, day_token, direction)
				elif m_compact:
					sign, n_s, day_token, direction = m_compact.groups()
					if sign or direction:
						target, human_hint = _parse_counted_weekday(today, n_s, day_token, direction, sign)

				m_future = re.fullmatch(r"(.+?)\s+([a-z]+)s?\s+(from now|ahead|later)", norm)
				m_past = re.fullmatch(r"(.+?)\s+([a-z]+)s?\s+ago", norm)

				if target is None and m_future:
					n_token, day_token, when_phrase = m_future.groups()
					n = _parse_int_maybe_words(n_token)
					day_name = _canonicalize_weekday(day_token)
					weekday = _WEEKDAY_CANON[day_name]
					target = _nth_weekday_from_today(today, weekday, n)
					human_hint = _("%(n)d %(day)s from now") % {"n": n, "day": day_name.capitalize()}

				elif target is None and m_past:
					n_token, day_token = m_past.groups()
					n = _parse_int_maybe_words(n_token)
					day_name = _canonicalize_weekday(day_token)
					weekday = _WEEKDAY_CANON[day_name]
					target = _nth_weekday_ago(today, weekday, n)
					human_hint = _("%(n)d %(day)s ago") % {"n": n, "day": day_name.capitalize()}

			# next/last/this <weekday>
			if target is None:
				parts = norm.split()
				if len(parts) == 2:
					prefix, day_token = parts
					try:
						day_name = _canonicalize_weekday(day_token)
					except Exception:
						day_name = None

					if day_name:
						weekday = _WEEKDAY_CANON[day_name]
						today_wd = today.weekday()

						if prefix == "next":
							days_ahead = (weekday - today_wd + 7) % 7
							days_ahead = 7 if days_ahead == 0 else days_ahead
							target = today + timedelta(days=days_ahead)
							human_hint = _("next %s") % day_name.capitalize()
						elif prefix == "last":
							days_back = (today_wd - weekday + 7) % 7
							days_back = 7 if days_back == 0 else days_back
							target = today - timedelta(days=days_back)
							human_hint = _("last %s") % day_name.capitalize()
						elif prefix == "this":
							days = weekday - today_wd
							target = today + timedelta(days=days)
							human_hint = _("this %s") % day_name.capitalize()

			# Calendar snippets copied without spacing, e.g. "05-06-202605/06/2026".
			if target is None:
				mm = _NUMERIC_DATE_RE.search(norm)
				if mm:
					target = self._parseNumericDate(today, mm.group(1), mm.group(3), mm.group(4), mm.group(2))
					human_hint = _("specific date")

			# Numeric UK-style calendar dates: 05/06/2026, 05-06-2026, 05.06.26, or 05/06.
			if target is None:
				mm = _NUMERIC_DATE_OPTIONAL_YEAR_RE.match(norm)
				if mm:
					first, sep, second, year_s = mm.groups()
					if year_s:
						target = self._parseNumericDate(today, first, second, year_s, sep)
					else:
						day = int(first)
						month = int(second)
						chosen_year = _choose_year_for_month_day(today, month, day, None)
						target = date(chosen_year, month, day)
					human_hint = _("specific date")

			# Day plus weekday, useful for calendar fragments such as "25 Fri" or "-25 Fri".
			if target is None:
				mm = _DAY_WEEKDAY_RE.match(norm)
				if mm:
					try:
						sign, day_s, weekday_s = mm.groups()
						day_name = _canonicalize_weekday(weekday_s)
						direction = -1 if sign == "-" else 1
						target = _date_with_day_and_weekday(today, int(day_s), _WEEKDAY_CANON[day_name], direction)
						human_hint = (_("previous") if direction < 0 else _("next")) + " " + day_name.capitalize() + " " + str(int(day_s))
						show_calendar_distance = True
					except Exception:
						pass

			if target is None:
				mm = _WEEKDAY_DAY_RE.match(norm)
				if mm:
					try:
						sign, weekday_s, day_s = mm.groups()
						day_name = _canonicalize_weekday(weekday_s)
						direction = -1 if sign == "-" else 1
						target = _date_with_day_and_weekday(today, int(day_s), _WEEKDAY_CANON[day_name], direction)
						human_hint = (_("previous") if direction < 0 else _("next")) + " " + day_name.capitalize() + " " + str(int(day_s))
						show_calendar_distance = True
					except Exception:
						pass

			# Strip an optional weekday from dates such as "Friday, 5 June 2026" or "5 June 2026 Friday".
			date_norm = norm
			typed_weekday = None
			mm = _WEEKDAY_PREFIX_RE.match(date_norm)
			if mm:
				try:
					typed_weekday = _canonicalize_weekday(mm.group(1))
					date_norm = mm.group(2)
				except Exception:
					pass
			mm = _WEEKDAY_SUFFIX_RE.match(date_norm)
			if mm:
				try:
					typed_weekday = _canonicalize_weekday(mm.group(2))
					date_norm = mm.group(1)
				except Exception:
					pass

			# Friendly month-name dates: DMY and MDY
			if target is None:
				mm = _FRIENDLY_DMY_OPTIONAL_YEAR_RE.match(date_norm)
				if mm:
					day_s, mon_s, year_s = mm.groups()
					day = int(day_s)
					month = _parse_month_token(mon_s)
					year = _parse_year_token(year_s) if year_s else None
					chosen_year = _choose_year_for_month_day(today, month, day, year)
					target = date(chosen_year, month, day)
					human_hint = _("specific date")

			if target is None:
				mm = _FRIENDLY_MDY_OPTIONAL_YEAR_RE.match(date_norm)
				if mm:
					mon_s, day_s, year_s = mm.groups()
					day = int(day_s)
					month = _parse_month_token(mon_s)
					year = _parse_year_token(year_s) if year_s else None
					chosen_year = _choose_year_for_month_day(today, month, day, year)
					target = date(chosen_year, month, day)
					human_hint = _("specific date")

			# ISO: YYYY-MM-DD
			if target is None:
				try:
					target = datetime.strptime(norm, "%Y-%m-%d").date()
				except Exception as e:
					raise ValueError(_("Unrecognized date format.")) from e
				human_hint = _("specific date")

			if target is not None and typed_weekday is not None:
				actual = calendar.day_name[target.weekday()].lower()
				if typed_weekday == actual:
					human_hint = _("specific date; weekday matches")
				else:
					human_hint = _("specific date; typed weekday was %(typed)s but the date is %(actual)s") % {
						"typed": typed_weekday.capitalize(),
						"actual": actual.capitalize(),
					}

		day_delta = (target - today).days

		return self._formatResult(original_text, target, human_hint, day_delta, total_days_already_explicit, show_calendar_distance)

	def _parseNumericDate(self, today, first_s, second_s, year_s, sep):
		first = int(first_s)
		second = int(second_s)

		if len(first_s) == 4:
			return date(first, second, int(year_s))

		# UK/default English interpretation: day/month/year.
		year = _parse_year_token(year_s)
		day = first
		month = second
		return date(year, month, day)

	def _formatResult(self, text, target, human_hint, day_delta, total_days_already_explicit, show_calendar_distance):
		lines = [
			_("Input: ") + text,
			_("Result: ") + target.strftime("%A, %B %d, %Y"),
		]

		if human_hint:
			lines.append(_("Meaning: ") + human_hint)

		if target == datetime.now().date():
			lines.append(_("Distance: today"))
		else:
			dist = _distance_between(datetime.now().date(), target)
			distance = _("%(dist)s ago") % {"dist": dist} if target < datetime.now().date() else _("in %(dist)s") % {"dist": dist}
			if (show_calendar_distance or not human_hint or (total_days_already_explicit and abs(day_delta) >= 60)) and distance != human_hint:
				lines.append(_("Distance: ") + distance)

		if not total_days_already_explicit:
			sign = "+" if day_delta > 0 else ""
			lines.append(_("Day offset: %(n)s days") % {"n": f"{sign}{day_delta}"})

		return "\n".join(lines)
