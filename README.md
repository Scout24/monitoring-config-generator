# This project is DEPRECATED and not any longer supported

monitoring-config-generator
===========================

Monitoring Config Generator reads a monitoring configuration as
YAML-data and writes an Icinga-configuration file as output.

Example YAML input:

```yaml
defaults:
    host_name: ${HOST_NAME}
    notification_period: 24x7
    check_period: 24x7
    contact_groups: testdienst
    notification_interval: 0
    notification_options: u,c,r
    max_check_attempts: 5
    check_interval: ${NORMAL_CHECK_INTERVAL}
    retry_interval: ${NORMAL_RETRY_INTERVAL}

variables:
    TYP: host
    LOC: test
    HOSTNR: '05'
    DOMAIN_NAME: other.domain
    GRP_HOST: testgrp05
    HOST_NAME: ${LOC}${TYP}${HOSTNR}
    NORMAL_CHECK_INTERVAL: 3
    NORMAL_RETRY_INTERVAL: 5
    FQDN: ${HOST_NAME}.${DOMAIN_NAME}
host:
    _processes:
      - "\"httpd -d\""
      - "\"icinga --config file\""
    address: ${FQDN}
    check_command: check-host-alive
    notification_interval: 30
    notification_options: d,u,r
    process_perf_data: 1
    retain_nonstatus_information: 1
services:
  mietcheck_status:
    _description: hier kommt die Beschreibung rein.
    check_command: check_httpd!/mietcheck/internal/status!80!"OK - Service is running"
    normal_check_interval: ${NORMAL_CHECK_INTERVAL}
    retry_check_interval: 1
    service_description: httpd
  diskusage_data:
    _description: hier kommt die Beschreibung rein.
    action_url: http://${GRP_HOST}/render/?from=-${NORMAL_CHECK_INTERVAL}min&target=alias(asPercent(${TYP}.${HOST_NAME}.system.diskspace._data.byte_used,sumSeries(${TYP}.${HOST_NAME}.system.diskspace._data.byte_used,${TYP}.${HOST_NAME}.system.diskspace._data.byte_free)),'disk_usage')
    check_command: check_graphite!90!95
    normal_check_interval: ${NORMAL_CHECK_INTERVAL}
    retry_check_interval: 1
    service_description: diskusage-data
```

This is a complex example that shows all the features. Important things to notice:
* Variable substitution happens at the very end
* Service IDs and service_descriptions must be unique.
* Don't use a tag _service_id, this will be filled with the ID of the service.
* This YAML could be split into several files that are merged on run-time (see below).

The resulting Icinga/Nagios configuration looks like this:
```
# Created by MonitoringConfigGenerator on 2013-06-26 13:07:05

define host {
        _processes                                   "httpd -d","icinga --config file"
        address                                      testhost05.other.domain
        check_command                                check-host-alive
        check_interval                               3
        check_period                                 24x7
        contact_groups                               testdienst
        host_name                                    testhost05
        max_check_attempts                           5
        notification_interval                        30
        notification_options                         d,u,r
        notification_period                          24x7
        process_perf_data                            1
        retain_nonstatus_information                 1
        retry_interval                               5
}

define service {
        _description                                 hier kommt die Beschreibung rein.
        _service_id                                  diskusage_data
        action_url                                   http://testgrp05/render/?from=-3min&target=alias(asPercent(host.testhost05.system.diskspace._data.byte_used,sumSeries(host.testhost05.system.diskspace._data.byte_used,host.testhost05.system.diskspace._data.byte_free)),'disk_usage')
        check_command                                check_graphite!90!95
        check_interval                               3
        check_period                                 24x7
        contact_groups                               testdienst
        host_name                                    testhost05
        max_check_attempts                           5
        normal_check_interval                        3
        notification_interval                        0
        notification_options                         u,c,r
        notification_period                          24x7
        retry_check_interval                         1
        retry_interval                               5
        service_description                          diskusage-data
}

define service {
        _description                                 hier kommt die Beschreibung rein.
        _service_id                                  mietcheck_status
        check_command                                check_httpd!/mietcheck/internal/status!80!"OK - Service is running"
        check_interval                               3
        check_period                                 24x7
        contact_groups                               testdienst
        host_name                                    testhost05
        max_check_attempts                           5
        normal_check_interval                        3
        notification_interval                        0
        notification_options                         u,c,r
        notification_period                          24x7
        retry_check_interval                         1
        retry_interval                               5
        service_description                          httpd
}
```

yaml-server => monitoring-config-generator => Icinga
----------------------------------------------------

monitoring-config-generator is closely related to the [yaml-server](https://github.com/ImmobilienScout24/yaml-server)
project. While yaml-server reads and merges YAML-configuration files
on a machine and then serves the result as YAML over HTTP,
monitoring-config-generator reads the merged YAML-configuration files
over HTTP and writes as output an Icinga-config.

Thus the basic flow of a information is:
YAML-files --> yaml-server --> monitoring-config-generator --> Icinga.

Input: URL or file or directory
-------------------------------

monitoring-config-generator accepts a single argument denoting the
input. This argument can be either one of
- a URL
- a file on the local machine
- a directory on the local machine

If the argument is not the path of a file or directory on the local
machine, it is assumed to be a URL and will be opened as such.

During normal operation the input should be the URL of a yaml-server.
Files and directories are supported mainly for testing purposes: in
order to test out your configuration you don't have to run it through
yaml-server, instead you can have monitoring-config-generator generate
the config from the file or directory of files directly.

Difference between files and directories: 

- If you specify a file, then monitoring-config-generator will read only
  this one file and generate an Icinga-config from that file.

- If your config is using multiple YAML-files in a directory which would
  usually be  merged by the yaml-server, specify this directory as input
  and monitoring-config-generator will merge them in a similar manner.


Merging of YAML-files: see yaml-server
------------------------------------------------------

The merging of YAML-files normally happens in yaml-server and is
documented there, so please read [yaml-server/Readme.md](https://github.com/ImmobilienScout24/yaml-server/blob/master/README.md) for details.


Output: You specify directory, filename is derived from filename or URL
-----------------------------------------------------------------------
The output is written to a file in a directory, whereas: 

The directory is usually /etc/icinga/conf.d/generated but can be changed using the
--targetdir option.

The filename is derived from the input:
- if the input is a url, the host will be used as filename
- if the input is a directory, the directory name will be used as filename
- if the input is a file, the filename without the extension will be uses as filename

Please be aware that the host will be used literally as name. There is
no notion of equality in monitoring-config-generator. Thus: even if in
your domain "1.2.3.4", "myserver.mydomain.mytld", and "myserver" are
the same host, calling monitoring-config-generator with these names as
input will generate 1.2.3.4.cfg, myserver.mydomain.mytld.cfg and
myserver.cfg respectively.


Using defaults
--------------
If after the merge of the YAML-files a section called 'defaults'
exists then it will be merged.  Defaults are merged is this: the
sections 'host' and each section in 'services' will be merged into a
new section filled with a copy of the defaults. Values defined in both
the default and the host-or-service will be merged the same way the
YAML-merge works on the yaml-server.

There are no host-only or service-only defaults.

First YAML-merge then defaults
------------------------------
Interaction between yaml-merge and defaults: first yaml-merge will be
performed, then defaults will be applied on the result of that
yaml-merge. Thus defaults defined in one YAML-file will affect hosts
or services defined in other YAML-files. Also defaults changed by the
YAML-merge of different files will only be applied in the finally
merged form.


Using variables
---------------
If after the merge of the YAML-files a section called 'variables'
exists, then variables will be substituted.  Variables are substituted
after the YAML-merge and after the application of defaults.

Variables will be substituted in all values of host and service
descriptions.

Variables are substituted like this:
- if variables contains a key-value pair "variable: value"
- then for each value in any host or service-definition
- the substring "${variable}" will be substituted with "value"
- variables can be replaced recursively
- variables are replaces as strings
- BUT: be aware if you write in YAML: "x: 05", then x will be "5" not
  "05". This is because YAML will treat x as a number. So use "x:
  '05'" instead if you want to treat it as string.


ETag support
------------
In order to frequently check for changes ETags are supported: When
loading a YAML-config from yaml-server, a header containing an ETag
will be set by the yaml-server.

The generated Icinga-config will contain the ETag inside an
Icinga-comment.

The next time monitoring-config-generator queries the server it will
first read the ETag from the already existing output file and pass the
ETag to the server. If the server responds with 304 Not Modified, then
monitoring-config-generator will not change the output file.

If the output-file doesn't exit, is not readable or contains no ETag
comment then monitoring-config-generator will send no ETag to the
server and instead always download a new configuration. 

Exit code
---------
The exit code will be 0 if a new config file was successfully
generated. It will also be 0 if the config file has not changed
because no change was detected.

The exit code will be non-zero if any kind of error occurred.

Detection of configuration changes
----------------------------------

Since the exit code is used for detecting errors it will be of
value 0 for both cases: successfully generating a new config and
not changing an already existing config. Thus the exit code cannot
be used for detecting configuration changes.

But: If the configuration does not change monitoring-config-generator
will not modify the existing file. So if you would want to have a feature
that restarts Icinga after any configuration change, you could run
monitoring-config-generator on all hosts and then restart Icinga if there
is any difference in any file in the directory of generated configuration
files.


Checks
------

In order to quickly fail on invalid generated Icinga-configurations,
the generated Icinga config will be subjected to some check before
monitoring-config-generator commits it to disc. It will not be written
in any check fails. The exit code of monitoring-config-generator will
be non-zero if any check fails.


Detecting failed checks
-----------------------

An existing config will not be overwritten if either an error occurs,
a check fails, or the config did not change.

Thus you should not check for differences in output files in order to
detect configuration errors. The only way to properly check for
configuration errors is to evaluate the exit-code of
monitoring-config-generator


Bypassing checks
----------------

If any check fails but you still want monitoring-config-generator to
write the generated Icinga-config, you can use the option
--skip-checks when running monitoring-config-generator.

This option could be useful for having a look at the generated
incorrect Icinga config to analyze and problems or to run that config
through Icinga.

