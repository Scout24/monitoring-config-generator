import datetime
import logging
import os
import os.path
import urlparse


import httplib2
import requests
import yaml


from .settings import CONFIG, ETAG_COMMENT
from .yaml_merger import merge_yaml_files
from .exceptions import MonitoringConfigGeneratorException


def is_file(parsed_uri):
    return parsed_uri.scheme in ['', 'file']


def is_host(parsed_uri):
    return parsed_uri.scheme in ['http', 'https']


def read_config(uri):
    uri_parsed = urlparse.urlparse(uri)
    if is_file(uri_parsed):
        return read_config_from_file(uri_parsed.path)
    elif is_host(uri_parsed):
        return read_config_from_host(uri)
    else:
        raise ValueError('Given url was not acceptable %s' % uri)


def read_config_from_file(path):
    yaml_config = merge_yaml_files(path)
    etag = None
    mtime = os.path.getmtime(path)
    return yaml_config, etag, mtime


def read_config_from_host(url):
    response = requests.get(url)

    def get_from_header(field):
        return response.headers[field] if field in response.headers else None

    if response.status_code == 200:
        yaml_config = yaml.load(response.content)
        etag = get_from_header('etag')
        mtime = get_from_header('last-modified')
        mtime = datetime.datetime.strptime(mtime, '%a, %d %b %Y %H:%M:%S %Z').strftime('%s')
    else:
        msg = "Request %s returned with status %s. I don't know how to handle that." % (url, response.status_code)
        raise MonitoringConfigGeneratorException(msg)

    return yaml_config, etag, mtime


class InputReader(object):

    def __init__(self, input_name, target_dir):
        self.logger = logging.getLogger("InputReader")
        self.input_name = input_name
        self.target_dir = target_dir
        self.init_host_name()
        self.init_output_path()

    def init_host_name(self):
        self.is_file = os.path.isfile(self.input_name)
        self.is_dir = os.path.isdir(self.input_name)
        if self.is_file:
            self.filename = self.input_name
            self.hostname, ext = os.path.splitext(os.path.basename(self.input_name))
        elif self.is_dir:
            self.filename = self.input_name
            self.hostname = os.path.basename(self.input_name)
        else:
            self.hostname = self.input_name

    def init_output_path(self):
        self.output_path = os.path.join(self.target_dir, self.hostname + '.cfg')

    def read_input(self):
        self.etag = None
        self.yaml_config = None
        self.config_changed = True
        if self.is_file or self.is_dir:
            self.logger.debug("Reading from file(s) %s for host %s" % (self.filename, self.hostname))
            self.yaml_config = merge_yaml_files(self.filename)
        else:
            self.logger.debug("Reading from host %s" % self.hostname)
            self.read_yaml_config_from_webserver()

    def read_yaml_config_from_webserver(self):
        """ will connect to hostname and retrieve the YAML config
                if no yaml could be loaded, yaml will be an empty string
                will also set self.etag
        """
        url = "http://" + self.hostname + ":" + CONFIG['PORT'] + CONFIG['RESOURCE']
        self.logger.debug("Retrieving config from URL: %s" % url)

        oldEtag = ETagReader(self.output_path).etag
        if oldEtag is not None:
            self.logger.debug("Using etag %s" % oldEtag)

        try:
            if oldEtag is not None:
                headers = {"If-None-Match": oldEtag}
            else:
                headers = {}

            response, content = (httplib2.Http()).request(url, "GET", headers=headers)
            status = response['status']
            self.logger.debug("Server responds with status %s" % status)
            if status == '200':
                self.etag = response.get('etag', None)
                self.yaml_config = yaml.load(content)
            elif status == '304':
                self.config_changed = False
                self.etag = oldEtag
            else:
                raise MonitoringConfigGeneratorException("Host %s returned with status %s.  "
                                                         "I don't know how to handle that." %
                                                             (self.hostname, status))
        except Exception, e:
            self.logger.error("Problem retrieving config for %s from %s" % (self.hostname, url), exc_info=True)
            self.etag = None
            self.yaml_config = None


class ETagReader(object):

    def __init__(self, fileName):
        self.fileName = fileName
        self.etag = None
        try:
            if os.path.isfile(fileName):
                with open(fileName, 'r') as configFile:
                    for line in configFile.xreadlines():
                        if line.startswith(ETAG_COMMENT):
                            etag = line.rstrip()[len(ETAG_COMMENT):]
                            if len(etag) > 0:
                                self.etag = etag
                                return
        except:
            # it is totally fine to not have an etag, in that case there
            # will just be no caching and the server will have to deliver the data again
            self.etag = None


