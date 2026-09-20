import builtins
from datetime import datetime, timedelta
import importlib.util
from pathlib import Path
import sys
import types
import unittest


def _load_plugin_module():
	builtins._ = lambda text: text

	global_plugin_handler = types.ModuleType("globalPluginHandler")
	global_plugin_handler.GlobalPlugin = object
	sys.modules["globalPluginHandler"] = global_plugin_handler

	script_handler = types.ModuleType("scriptHandler")
	script_handler.script = lambda **kwargs: lambda func: func
	sys.modules["scriptHandler"] = script_handler

	ui = types.ModuleType("ui")
	ui.message = lambda message: None
	sys.modules["ui"] = ui

	addon_handler = types.ModuleType("addonHandler")
	addon_handler.initTranslation = lambda: None
	sys.modules["addonHandler"] = addon_handler

	wx = types.ModuleType("wx")
	wx.Dialog = object
	sys.modules["wx"] = wx

	gui = types.ModuleType("gui")
	gui.mainFrame = None
	sys.modules["gui"] = gui

	plugin_path = Path(__file__).parents[1] / "source" / "globalPlugins" / "dateParser.py"
	spec = importlib.util.spec_from_file_location("dateParserPlugin", plugin_path)
	module = importlib.util.module_from_spec(spec)
	spec.loader.exec_module(module)
	return module


date_parser = _load_plugin_module()


class DurationParsingTests(unittest.TestCase):
	def setUp(self):
		self.now = datetime(2026, 9, 20, 12, 0, 0)

	def test_large_compact_hours(self):
		result = date_parser._parse_duration_expression("28000h", self.now)
		self.assertEqual(100_800_000, result.total_seconds)
		self.assertEqual("1,166 days, 16 hours", result.duration_text)
		self.assertEqual(self.now + timedelta(hours=28_000), result.target)

	def test_negative_word_hours(self):
		result = date_parser._parse_duration_expression("-28000 hours", self.now)
		self.assertEqual(-100_800_000, result.total_seconds)
		self.assertEqual("1,166 days, 16 hours", result.duration_text)
		self.assertEqual(self.now - timedelta(hours=28_000), result.target)

	def test_seconds_ago(self):
		result = date_parser._parse_duration_expression("5000s ago", self.now)
		self.assertEqual(-5_000, result.total_seconds)
		self.assertEqual("1 hour, 23 minutes, 20 seconds", result.duration_text)
		self.assertEqual(self.now - timedelta(seconds=5_000), result.target)

	def test_mixed_time_units(self):
		result = date_parser._parse_duration_expression("2h 30min 15s", self.now)
		self.assertEqual(9_015, result.total_seconds)
		self.assertEqual("2 hours, 30 minutes, 15 seconds", result.duration_text)

	def test_natural_minutes_from_now(self):
		result = date_parser._parse_duration_expression("in 90 minutes", self.now)
		self.assertEqual(5_400, result.total_seconds)
		self.assertEqual("1 hour, 30 minutes", result.duration_text)

	def test_month_abbreviation_remains_a_date_offset(self):
		self.assertIsNone(date_parser._parse_duration_expression("5m", self.now))

	def test_unit_without_a_number_is_not_a_duration(self):
		self.assertIsNone(date_parser._parse_duration_expression("hours", self.now))

	def test_formatted_result_includes_duration_and_timestamp(self):
		result = date_parser._parse_duration_expression("-5000s", self.now)
		formatted = date_parser._format_duration_result("-5000s", result)
		self.assertIn("Duration: 1 hour, 23 minutes, 20 seconds", formatted)
		self.assertIn("Meaning: 1 hour, 23 minutes, 20 seconds ago", formatted)
		self.assertIn("Result: Sunday, September 20, 2026 at 10:36:40", formatted)

	def test_duration_is_routed_through_main_parser(self):
		plugin = object.__new__(date_parser.GlobalPlugin)
		formatted = plugin._parseDateExpression("5000s ago")
		self.assertIn("Duration: 1 hour, 23 minutes, 20 seconds", formatted)
		self.assertIn("Meaning: 1 hour, 23 minutes, 20 seconds ago", formatted)

	def test_existing_month_offset_still_uses_date_parser(self):
		plugin = object.__new__(date_parser.GlobalPlugin)
		formatted = plugin._parseDateExpression("5m")
		self.assertIn("Meaning: 5m from now", formatted)
		self.assertNotIn("Duration:", formatted)


if __name__ == "__main__":
	unittest.main()
