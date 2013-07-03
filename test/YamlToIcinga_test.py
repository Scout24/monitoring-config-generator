import os
import unittest

os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.MonitoringConfigGenerator import YamlToIcinga


class Test(unittest.TestCase):

    def test_text_to_cvs(self):
        self.assertEquals("", YamlToIcinga.value_to_icinga(""))
        self.assertEquals("text", YamlToIcinga.value_to_icinga("text"))

    def test_number_to_cvs(self):
        self.assertEquals("42", YamlToIcinga.value_to_icinga(42))
        self.assertEquals("-1", YamlToIcinga.value_to_icinga(-1))
        self.assertEquals("-1.6", YamlToIcinga.value_to_icinga(-1.6))

    def test_list_to_cvs(self):
        self.assertEquals("", YamlToIcinga.value_to_icinga([]))
        self.assertEquals("a", YamlToIcinga.value_to_icinga(["a"]))
        self.assertEquals("a,b", YamlToIcinga.value_to_icinga(["a", "b"]))
        self.assertEquals("a,,b", YamlToIcinga.value_to_icinga(["a", None, "b"]))
        self.assertEquals(",,,", YamlToIcinga.value_to_icinga([None, None, None, None]))
        self.assertEquals(",23,42,", YamlToIcinga.value_to_icinga([None, "23", 42, None]))

