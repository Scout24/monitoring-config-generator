__author__ = 'mhoyer'

import unittest
from monitoring_config_generator.icinga2.config import Config

class ConfigTests(unittest.TestCase):

    def setUp(self):
        self.config = Config()

    def tests_write_object_creates_simple_configuration(self):
        EXPECTED = ['', "object Host 'myHost' {", 'address = 10.10.10.10', '}']
        self.config.write_object("Host", "myHost", {"address":"10.10.10.10"})
        self.assertEqual(EXPECTED, self.config.lines)

    def tests_write_object_creates_simple_configuration(self):
        EXPECTED = ['', "object Host 'myHost' {", 'address = 10.10.10.10', '}']
        self.config.write_object("Host", "myHost", {"address":"10.10.10.10"})
        self.assertEqual(EXPECTED, self.config.lines)

    def tests_format_value_returns_empty_string_if_none_supplied(self):
        VALUE = None
        EXPECTED = ""
        self.assertEqual(EXPECTED, self.config._format_value(VALUE))

    def tests_format_value_returns_list_as_string(self):
        VALUE = ["A", "B", "C"]
        EXPECTED = "[A,B,C]"
        self.assertEqual(EXPECTED, self.config._format_value(VALUE))

    def tests_format_value_returns_empty_list_as_empty_string(self):
        VALUE = []
        EXPECTED = ""
        self.assertEqual(EXPECTED, self.config._format_value(VALUE))

    def tests_format_value_returns_int_as_string(self):
        VALUE = 12
        EXPECTED = "12"
        self.assertEqual(EXPECTED, self.config._format_value(VALUE))

    def tests_format_value_returns_zero_int_as_string(self):
        VALUE = 0
        EXPECTED = "0"
        self.assertEqual(EXPECTED, self.config._format_value(VALUE))

    def tests_clean_string_removes_special_characters(self):
        VALUE = """a!\"#$%&'( e )*b+,./:;<=>?@[\]^`c{|}~d"""
        EXPECTED = "a( e )bcd"
        self.assertEqual(EXPECTED, self.config._clean_string(VALUE))