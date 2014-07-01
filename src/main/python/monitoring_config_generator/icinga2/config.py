__author__ = 'mhoyer'

class Config(object):

    def __init__(self):
        self.lines = []

    def write_line(self, line):
        self.lines.append(line)

    def write_object(self, object_type, object_name, object_data):
        self.write_line("")
        self.write_line("object %s '%s' {" % (object_type,object_name))
        sorted_keys = object_data.keys()
        sorted_keys.sort()
        for key in sorted_keys:
            value = object_data[key]
            # TODO: what shall we do with config items without '=' as separator like 'import generic-host'
            self.lines.append(("%s = %s" % (key, self.value_to_icinga(value))))
        self.write_line("}")

    @staticmethod
    def value_to_icinga(value):
        """Convert a scalar or list to Icinga value format. Lists are concatenated by ,
        and empty (None) values produce an empty string"""
        if isinstance(value, list):
            # explicitly set None values to empty string
            return ",".join([str(x) if (x is not None) else "" for x in value])
        else:
            return str(value)