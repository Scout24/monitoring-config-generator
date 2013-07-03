#!/usr/bin/env python

from setuptools import setup
from distutils.command.clean import clean
import os
import shutil

class completeClean(clean):
    def run(self):
        if os.path.exists(self.build_base):
            shutil.rmtree(self.build_base)
            
        dist_dir = 'dist'
        if os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)
        dist_dir = "deb_dist"
        if os.path.exists(dist_dir):
            shutil.rmtree(dist_dir)
        

setup(
    name="monitoring-config-generator",
    version=1,
    author="Felix Sperling",
    description="Get monitoring configuration in YAML format via HTTP and generate icinga host and check config",
    license="GPL",
    keywords="yaml icinga http",
    url="https://github.com/ImmobilienScout24/monitoring-config-generator.git",
    packages=[ "monitoring_config_generator" ],
    test_suite="test",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "Programming Language :: Python",
        ],
    #scripts = ["bin/monitoring_config_generator"],
    entry_points={
        'console_scripts': [
              'monitoring_config_generator = monitoring_config_generator.MonitoringConfigGenerator:main_method',
        ],
    },
     cmdclass={'clean' : completeClean},
)
