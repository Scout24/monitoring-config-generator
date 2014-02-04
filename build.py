
from pybuilder.core import use_plugin, init, Author

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin('python.install_dependencies')
use_plugin('python.distutils')

name = "monitoring-config-generator"
default_task = "publish"

authors = [Author('Schlomo Schapiro', ''),
           Author('Sven Schindler', ''),
           Author('Jan Gaedicke', ''),
           Author('Valentin Haenel', ''),
           Author('Marco Hoyer', ''),
           ]
license="GPL"
description="Get monitoring configuration in YAML format via HTTP and generate icinga host and check config"
summary = "Fluent interface facade for Michael Foord's mock."
version = '4'
url="https://github.com/ImmobilienScout24/monitoring-config-generator.git"


@init
def set_properties(project):
    project.depends_on('pyyaml')
    project.depends_on('httplib2')
    project.set_property('distutils_classifiers', [
        "Development Status :: 4 - Beta",
        "Topic :: Utilities",
        "Programming Language :: Python",
        ])
