import os
import unittest


from mock import patch, Mock


os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.readers import (read_config,
                                                 read_config_from_file,
                                                 read_config_from_host,
                                                 read_etag,
                                                 )
from monitoring_config_generator.exceptions import MonitoringConfigGeneratorException


class TestReadEtag(unittest.TestCase):

    def test_reads_etag_from_file(self):
        self.assertEquals("754d61019fb8a470a654c25e59b10311963f00b5e2d2784712732feed6a82066",
                          read_etag("testdata/etag/testhost01.some.domain.etag.cfg"))

    def test_file_exists_but_null_etag(self):
        self.assertEquals(None, read_etag("testdata/etag/testhost01.some.domain.nulletag.cfg"))

    def test_file_exists_but_no_etag(self):
        self.assertEquals(None, read_etag("testdata/etag/testhost01.some.domain.noetag.cfg"))

    def test_file_does_not_exist(self):
        self.assertEquals(None, read_etag("idontex.st"))


ANY_PATH = '/path/to/file'


class TestConfigReaders(unittest.TestCase):

    @patch('monitoring_config_generator.readers.read_config_from_file')
    def test_read_config_calls_read_config_from_file_with_file_uri(
            self, mock_read_config_from_file):
        for i, uri in enumerate([ANY_PATH, 'file://' + ANY_PATH]):
            read_config(uri)
            mock_read_config_from_file.assert_called_with(ANY_PATH)
            self.assertEquals(i + 1, mock_read_config_from_file.call_count)

    @patch('monitoring_config_generator.readers.read_config_from_host')
    def test_read_config_calls_read_config_from_host_with_host_uri(
            self, mock_read_config_from_host):
        for i, uri in enumerate(['http://example.com', 'https://example.com']):
            read_config(uri)
            self.assertEquals(i + 1, mock_read_config_from_host.call_count)

    def test_read_config_raises_exception_with_invalid_uri(self):
        self.assertRaises(ValueError, read_config, 'ftp://example.com')

    @patch('monitoring_config_generator.readers.merge_yaml_files')
    @patch('os.path.getmtime')
    def test_read_config_from_file(self, getmtime_mock, merge_yaml_files_mock):
        ANY_MERGED_YAML = 'any_yaml'
        ANY_MTIME = 123456789.0
        merge_yaml_files_mock.return_value = ANY_MERGED_YAML
        getmtime_mock.return_value = ANY_MTIME
        merged_yaml, etag, mtime = read_config_from_file(ANY_PATH)
        merge_yaml_files_mock.assert_called_once_with(ANY_PATH)
        getmtime_mock.assert_called_once_with(ANY_PATH)
        self.assertEquals(ANY_MERGED_YAML, merged_yaml)
        self.assertEquals(ANY_MTIME, mtime)

    @patch('requests.get')
    def test_read_config_from_host(self, get_mock):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.content = 'yaml:'
        response_mock.headers = {'etag': 'deadbeefbeebaadfoodbabe',
                                 'last-modified': 'Thu, 01 Jan 1970 01:00:00 GMT'
                                 }
        get_mock.return_value = response_mock
        merged_yaml, etag, mtime = read_config_from_host(ANY_PATH)
        self.assertEquals({'yaml': None}, merged_yaml)
        self.assertEquals('deadbeefbeebaadfoodbabe', etag)
        self.assertEquals('0', mtime)

    @patch('requests.get')
    def test_read_config_from_host_raises_exception(self, get_mock):
        response_mock = Mock()
        response_mock.status_code = 404
        get_mock.return_value = response_mock
        self.assertRaises(MonitoringConfigGeneratorException,
                          read_config_from_host, ANY_PATH)
