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
	r"^\s*(\d{1,2})\s*[-/ ]\s*([a-zA-Z]+)\.?\s*(?:[-/ ]\s*(\d{4}))?\s*$"
)
_FRIENDLY_MDY_OPTIONAL_YEAR_RE = re.compile(
	r"^\s*([a-zA-Z]+)\.?\s*[-/ ]\s*(\d{1,2})\s*(?:[-/ ,]\s*(\d{4}))?\s*$"
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


def _choose_year_for_month_day(today: date, month: int, day: int, year):
	if year is not None:
		return year
	this_year = today.year
	candidate = date(this_year, month, day)
	return this_year if candidate >= today else this_year + 1


def _last_day_of_month(year: int, month: int) -> int:
	return calendar.monthrange(year, month)[1]


def _add_months(d: date, months: int) -> date:
	y = d.year + (d.month - 1 + months) // 12
	m = (d.month - 1 + months) % 12 + 1
	day = min(d.day, _last_day_of_month(y, m))
	return date(y, m, day)


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


def _apply_compact_relative(today: date, text: str):
	norm = re.sub(r"\s+", " ", text.strip().lower())

	direction = None
	m_dir = re.search(r"\s+(ago|from now|ahead|later)\s*$", norm)
	if m_dir:
		direction = m_dir.group(1)
		norm = re.sub(r"\s+(ago|from now|ahead|later)\s*$", "", norm).strip()

	tokens = _MULTI_COMPACT_REL_TOKEN_RE.findall(norm)
	if not tokens:
		raise ValueError(_("No relative tokens found."))

	if direction == "ago":
		sign = -1
	elif direction in ("from now", "ahead", "later"):
		sign = 1
	else:
		# No direction word: infer from sign of any token; otherwise assume future.
		sign = -1 if any(int(n) < 0 for n, u in tokens) else 1

	years = months = weeks = days = 0
	for n_s, u in tokens:
		n = abs(int(n_s))
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
		target = _add_months(target, sign * total_months)
	if weeks or days:
		target = target + timedelta(days=sign * (weeks * 7 + days))

	parts = []
	if years: parts.append(f"{years}y")
	if months: parts.append(f"{months}m")
	if weeks: parts.append(f"{weeks}w")
	if days: parts.append(f"{days}d")
	hint = " ".join(parts) if parts else ""
	hint = (hint + " ago") if sign < 0 else (hint + " from now")

	# Only suppress Day offset line when user already expressed a days-only offset.
	total_days_already_explicit = (years == 0 and months == 0 and weeks == 0 and days != 0)
	return target, hint.strip(), total_days_already_explicit


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
		if key in (wx.WXK_ESCAPE, wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER):
			self.EndModal(wx.ID_OK)
			return
		event.Skip()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

	@script(
		description=_("Parse a date expression and show the result"),
		gesture="kb:NVDA+e"
	)
	def script_dateInput(self, gesture):
		wx.CallAfter(self._showInputDialog)

	def _showInputDialog(self):
		text = ""
		try:
			dlg = wx.TextEntryDialog(
				gui.mainFrame,
				_("Enter a date expression (e.g. tomorrow, mon, next Thu, 5d, -5d, 2w from now, 1y, 5y 4m 3w 2d, 1992-09-01, 13 Apr 2026, Mar 5):"),
				_("Date parser")
			)

			if dlg.ShowModal() != wx.ID_OK:
				dlg.Destroy()
				return

			text = (dlg.GetValue() or "").strip().lower()
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
				+ _("Try: tomorrow, mon, next Thu, 5d, -5d, 2w from now, 1y, 5y 4m 3w 2d, -365, YYYY-MM-DD, 13 Apr 2026, 5 Mar, or Mar 5.")
			)
			ui.message(_("Error: invalid date expression."))
			self._showResultDialog(msg)

	def _showResultDialog(self, resultText):
		dlg = ResultDialog(gui.mainFrame, _("Date parser result"), resultText)
		dlg.ShowModal()
		dlg.Destroy()

	def _parseDateExpression(self, text):
		today = datetime.now().date()
		target = None
		human_hint = ""
		total_days_already_explicit = False

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

		# Compact relative units: 5d, -5d, 2w from now, 1y, 5y 4m 3w 2d
		if target is None and _MULTI_COMPACT_REL_RE.match(text):
			target, human_hint, total_days_already_explicit = _apply_compact_relative(today, text)

		if target is None:
			norm = re.sub(r"\s+", " ", text.strip().lower())

			# N weekday(s) from now / ago
			m_future = re.fullmatch(r"(.+?)\s+([a-z]+)s?\s+(from now|ahead|later)", norm)
			m_past = re.fullmatch(r"(.+?)\s+([a-z]+)s?\s+ago", norm)

			if m_future:
				n_token, day_token, when_phrase = m_future.groups()
				n = _parse_int_maybe_words(n_token)
				day_name = _canonicalize_weekday(day_token)
				weekday = _WEEKDAY_CANON[day_name]
				target = _nth_weekday_from_today(today, weekday, n)
				human_hint = _("%(n)d %(day)s from now") % {"n": n, "day": day_name.capitalize()}

			elif m_past:
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

			# Friendly month-name dates: DMY and MDY
			if target is None:
				mm = _FRIENDLY_DMY_OPTIONAL_YEAR_RE.match(text)
				if mm:
					day_s, mon_s, year_s = mm.groups()
					day = int(day_s)
					month = _parse_month_token(mon_s)
					year = int(year_s) if year_s else None
					chosen_year = _choose_year_for_month_day(today, month, day, year)
					target = date(chosen_year, month, day)
					human_hint = _("specific date")

			if target is None:
				mm = _FRIENDLY_MDY_OPTIONAL_YEAR_RE.match(text)
				if mm:
					mon_s, day_s, year_s = mm.groups()
					day = int(day_s)
					month = _parse_month_token(mon_s)
					year = int(year_s) if year_s else None
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

		day_delta = (target - today).days

		if target == today:
			relation = _("is today")
		else:
			dist = _distance_between(today, target)
			relation = _("was %(dist)s ago") % {"dist": dist} if target < today else _("is in %(dist)s") % {"dist": dist}

		hint_line = (_("Interpretation: ") + human_hint + "\n") if human_hint else ""

		day_offset_line = ""
		if not total_days_already_explicit:
			sign = "+" if day_delta > 0 else ""
			day_offset_line = _("Day offset: %(n)s days") % {"n": f"{sign}{day_delta}"} + "\n"

		return (
			_("Input: ") + text + "\n"
			+ hint_line
			+ _("Resolved date: ") + target.strftime("%A, %B %d, %Y") + "\n"
			+ _("Relation: ") + relation + "\n"
			+ day_offset_line
		).rstrip()
