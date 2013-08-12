class MonitoringConfigGeneratorException(Exception):
    def __init__(self,message=""):
        self.message=message

    def __str__(self):
        return self.message


class IcingaCheckException(MonitoringConfigGeneratorException):
    def __init__(self,message=""):
        self.message=message


class UnknownSectionException(IcingaCheckException):
    def __init__(self,message=""):
        self.message=message


class MandatoryDirectiveMissingException(IcingaCheckException):
    def __init__(self,message=""):
        self.message=message


class HostNamesNotEqualException(IcingaCheckException):
    def __init__(self,message=""):
        self.message=message


class ServiceDescriptionNotUniqueException(IcingaCheckException):
    def __init__(self,message=""):
        self.message=message
        
class InvalidFormatException(MonitoringConfigGeneratorException):
    def __init__(self,message=""):
        self.message=message


