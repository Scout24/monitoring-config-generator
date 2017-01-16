import os
import unittest
from mock import Mock

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

    def _get_config_mock(self, host=None, services=None):
        config = Mock()
        config.host = host or {}
        config.services = services or {}
        return config

    def test_write_section_forbidden_characters(self):
        # Malicious hosts may try to insert new sections, e.g. by setting a
        # value to  "42\n}\n define command {\n ......" which would lead to
        # arbitrary code execution. Therefore, certain characters must be
        # forbidden.
        header = Mock()
        header.serialize.return_value = "the header"

        for forbidden in '\n', '}':
            # Forbidden character in 'host' section.
            config = self._get_config_mock(host={'key': 'xx%syy' % forbidden})
            self.assertRaises(Exception, YamlToIcinga, config, header)
            config = self._get_config_mock(host={'xx%syy' % forbidden: "value"})
            self.assertRaises(Exception, YamlToIcinga, config, header)

            config = self._get_config_mock(services={'foo': 'xx%syy' % forbidden})
            self.assertRaises(Exception, YamlToIcinga, config, header)
            config = self._get_config_mock(services={'xx%syy' % forbidden: "value"})
            self.assertRaises(Exception, YamlToIcinga, config, header)
