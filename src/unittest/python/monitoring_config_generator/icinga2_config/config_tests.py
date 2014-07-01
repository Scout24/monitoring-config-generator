__author__ = 'mhoyer'

import unittest
from monitoring_config_generator.icinga2.config import Config

class ConfigTests(unittest.TestCase):

    def tests_write_object_creates_simple_configuration(self):
        EXPECTED = ['', "object Host 'myHost' {", 'address = 10.10.10.10', '}']
        config = Config()
        config.write_object("Host", "myHost", {"address":"10.10.10.10"})
        self.assertEqual(config.lines, EXPECTED)