class MonitoringConfigGeneratorException(Exception):
    pass


class IcingaCheckException(MonitoringConfigGeneratorException):
    pass


class UnknownSectionException(IcingaCheckException):
    pass


class MandatoryDirectiveMissingException(IcingaCheckException):
    pass


class HostNamesNotEqualException(IcingaCheckException):
    pass


class ServiceDescriptionNotUniqueException(IcingaCheckException):
    pass


class InvalidFormatException(MonitoringConfigGeneratorException):
    pass


class ConfigurationContainsUndefinedVariables(IcingaCheckException):
    pass


class NoSuchHostname(Exception):
    pass

class HostUnreachableException(MonitoringConfigGeneratorException):
    pass
