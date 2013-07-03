import glob
import os
import yaml


def dict_merge(a, b):
    """merges b into a
    based on http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    and extended to also merge arrays and to replace the content of keys with the same name"""
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key].extend(b[key])
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]


def merge_yaml_files(d):
    data = {}
    files = []
    if os.path.isfile(d):
        files = [d]
    else:
        files = sorted(glob.glob(os.path.join(d, '*.yaml')))

    for f in files:
        new_data = yaml.safe_load(file(f))
        dict_merge(data, new_data)

    return data
