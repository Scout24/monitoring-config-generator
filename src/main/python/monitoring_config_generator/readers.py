import datetime
import os
import os.path
import urlparse


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


def read_etag(file_name):
    try:
        with open(file_name, 'r') as config_file:
            for line in config_file.xreadlines():
                if line.startswith(ETAG_COMMENT):
                    etag = line.rstrip()[len(ETAG_COMMENT):]
                    if len(etag) > 0:
                        return etag
    except IOError:
        # it is totally fine to not have an etag, in that case there
        # will just be no caching and the server will have to deliver the data again
        pass
