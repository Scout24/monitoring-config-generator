
from pybuilder.core import use_plugin, init, Author

use_plugin("python.core")
use_plugin("python.unittest")
use_plugin('python.install_dependencies')
use_plugin('python.distutils')
use_plugin('python.coverage')
use_plugin('copy_resources')

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
version = '5'
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
    project.set_property('copy_resources_target', '$dir_dist')
    project.get_property('copy_resources_glob').extend(
            ['setup.cfg', 'LICENSE.TXT', 'README.md', 'MANIFEST.in'])

@init(environments='teamcity')
def set_properties_for_teamcity_builds(project):
    import os
    project.version = '%s-%s' % (project.version, os.environ.get('BUILD_NUMBER', 0))
    project.default_task = ['install_dependencies', 'publish']
