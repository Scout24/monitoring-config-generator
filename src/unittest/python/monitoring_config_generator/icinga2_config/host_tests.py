__author__ = 'mhoyer'

import unittest
from monitoring_config_generator.icinga2.host import Host


class HostTests(unittest.TestCase):

    def test_host_object_creates_valid_icinga2_config(self):
        host = Host()
