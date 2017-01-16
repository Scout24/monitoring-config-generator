import os
import unittest2
import time
import socket

from mock import patch, Mock
from requests import RequestException
from requests.exceptions import Timeout


os.environ['MONITORING_CONFIG_GENERATOR_CONFIG'] = "testdata/testconfig.yaml"
from monitoring_config_generator.yaml_tools.readers import (read_config,
                                                            read_config_from_file,
                                                            read_config_from_host,
                                                            Header)
from monitoring_config_generator.exceptions import MonitoringConfigGeneratorException, HostUnreachableException


class TestHeader(unittest2.TestCase):
    def test_constructor(self):
        header = Header(etag='a', mtime=1)
        self.assertEquals(header.etag, 'a')
        self.assertEquals(header.mtime, 1)

    def test_compare_myheader_is_newer_than_yours_with_equal_mtime(self):
        # In case of different etags but same mtime, clock-skew (???)
        # don't touch anything!
        my_header = Header(etag='a', mtime=0)
        your_header = Header(etag='b', mtime=0)
        self.assertFalse(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_newer_than_yours(self):
        my_header = Header(etag='a', mtime=1)
        your_header = Header(etag='b', mtime=0)
        self.assertTrue(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_not_newer_than_yours_with_older_mtime(self):
        my_header = Header(etag='a', mtime=0)
        your_header = Header(etag='b', mtime=1)
        self.assertFalse(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_not_newer_than_yours_with_equal_etag(self):
        my_header = Header(etag='a', mtime=0)
        your_header = Header(etag='a', mtime=0)
        self.assertFalse(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_not_newer_than_yours_with_equal_etag_and_newer_mtime(self):
        my_header = Header(etag='a', mtime=1)
        your_header = Header(etag='a', mtime=0)
        self.assertFalse(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_not_newer_than_yours_with_equal_etag_and_older_mtime(self):
        my_header = Header(etag='a', mtime=0)
        your_header = Header(etag='a', mtime=1)
        self.assertFalse(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_not_newer_than_yours_with_None(self):
        my_header = Header(etag=None, mtime=0)
        your_header = Header(etag=None, mtime=0)
        self.assertFalse(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_newer_than_yours_with_differing_mtime(self):
        my_header = Header(etag=None, mtime=1)
        your_header = Header(etag=None, mtime=0)
        self.assertTrue(my_header.is_newer_than(your_header))

    def test_compare_myheader_is_not_newer_than_yours_with_differing_mtime(self):
        my_header = Header(etag=None, mtime=0)
        your_header = Header(etag=None, mtime=1)
        self.assertFalse(my_header.is_newer_than(your_header))


class TestReadEtag(unittest2.TestCase):
    def test_reads_etag_from_file(self):
        etag = "754d61019fb8a470a654c25e59b10311963f00b5e2d2784712732feed6a82066"
        expected = Header(etag=etag)
        received = Header.parse("testdata/etag/testhost01.some.domain.etag.cfg")
        self.assertEquals(expected.etag, received.etag)

    def test_file_exists_but_null_etag(self):
        received = Header.parse("testdata/etag/testhost01.some.domain.nulletag.cfg")
        self.assertEquals(Header(), received)

    def test_file_exists_but_no_etag(self):
        received = Header.parse("testdata/etag/testhost01.some.domain.noetag.cfg")
        self.assertEquals(Header(), received)

    def test_file_does_not_exist(self):
        received = Header.parse("idontex.st")
        self.assertEquals(Header(), received)


ANY_PATH = '/path/to/file'


class TestConfigReaders(unittest2.TestCase):
    @patch('monitoring_config_generator.yaml_tools.readers.read_config_from_file')
    def test_read_config_calls_read_config_from_file_with_file_uri(
            self, mock_read_config_from_file):
        for i, uri in enumerate([ANY_PATH, 'file://' + ANY_PATH]):
            read_config(uri)
            mock_read_config_from_file.assert_called_with(ANY_PATH)
            self.assertEquals(i + 1, mock_read_config_from_file.call_count)

    @patch('monitoring_config_generator.yaml_tools.readers.read_config_from_host')
    def test_read_config_calls_read_config_from_host_with_host_uri(
            self, mock_read_config_from_host):
        for i, uri in enumerate(['http://example.com', 'https://example.com']):
            read_config(uri)
            self.assertEquals(i + 1, mock_read_config_from_host.call_count)

    def test_read_config_raises_exception_with_invalid_uri(self):
        self.assertRaises(ValueError, read_config, 'ftp://example.com')

    @patch('monitoring_config_generator.yaml_tools.readers.merge_yaml_files')
    @patch('os.path.getmtime')
    def test_read_config_from_file(self, getmtime_mock, merge_yaml_files_mock):
        ANY_MERGED_YAML = 'any_yaml'
        ANY_MTIME = 123456789.0
        merge_yaml_files_mock.return_value = ANY_MERGED_YAML
        getmtime_mock.return_value = ANY_MTIME
        merged_yaml, header = read_config_from_file(ANY_PATH)
        merge_yaml_files_mock.assert_called_once_with(ANY_PATH)
        getmtime_mock.assert_called_once_with(ANY_PATH)
        self.assertEquals(ANY_MERGED_YAML, merged_yaml)
        self.assertEquals(ANY_MTIME, header.mtime)

    @patch('requests.get')
    def test_read_config_from_host(self, get_mock):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.content = 'yaml:'
        response_mock.headers = {'etag': 'deadbeefbeebaadfoodbabe',
                                 'last-modified': 'Thu, 01 Jan 1970 01:00:00 GMT'}
        get_mock.return_value = response_mock
        merged_yaml, header = read_config_from_host(ANY_PATH)
        self.assertEquals({'yaml': None}, merged_yaml)
        self.assertEquals('deadbeefbeebaadfoodbabe', header.etag)
        self.assertEquals(0, header.mtime)

    @patch('requests.get')
    def test_read_config_from_host_without_mtime(self, get_mock):
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.content = 'yaml:'
        response_mock.headers = {'etag': 'deadbeefbeebaadfoodbabe'}
        get_mock.return_value = response_mock
        merged_yaml, header = read_config_from_host(ANY_PATH)

        self.assertAlmostEquals(int(time.time()), header.mtime)

    @patch('requests.get')
    def test_read_config_from_host_rejects_multiline_etag(self, get_mock):
        # To prevent config-injection, etag must not be a multi-line string.
        response_mock = Mock()
        response_mock.status_code = 200
        response_mock.content = 'yaml:'
        response_mock.headers = {'etag': 'first line\nsecond line'}
        get_mock.return_value = response_mock
        self.assertRaises(Exception, read_config_from_host, ANY_PATH)

    @patch('requests.get')
    def test_read_config_from_host_raises_exception_on_404(self, get_mock):
        response_mock = Mock()
        response_mock.status_code = 404
        get_mock.return_value = response_mock
        with self.assertRaises(MonitoringConfigGeneratorException):
            read_config_from_host(ANY_PATH)

    @patch('requests.get')
    def test_read_config_from_host_raises_host_unreachable_exception_if_there_is_a_socket_gaierror(self, get_mock):
        get_mock.side_effect = socket.gaierror
        with self.assertRaises(HostUnreachableException):
            read_config_from_host(ANY_PATH)

    @patch('requests.get')
    def test_read_config_from_host_raises_host_unreachable_exception_if_there_is_a_socket_error(self, get_mock):
        get_mock.side_effect = socket.error
        with self.assertRaises(HostUnreachableException):
            read_config_from_host(ANY_PATH)

    @patch('requests.get')
    def test_read_config_from_host_raises_host_unreachable_exception_if_there_is_a_timeout_error(self, get_mock):
        get_mock.side_effect = Timeout
        with self.assertRaises(HostUnreachableException):
            read_config_from_host(ANY_PATH)

    @patch('requests.get')
    def test_read_config_from_host_raises_exception_on_any_other_requests_error(self, get_mock):
        get_mock.side_effect = RequestException
        with self.assertRaises(MonitoringConfigGeneratorException):
            read_config_from_host(ANY_PATH)