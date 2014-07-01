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
            self.lines.append(("%s = %s" % (key, self._format_value(value))))
        self.write_line("}")

    @staticmethod
    def _clean_string(string):
        exclude_list = set("!\"#$%&'*+,./:;<=>?@[\]^`{|}~")
        clean_string = ''.join(character for character in string if character not in exclude_list)
        return clean_string.strip()

    @staticmethod
    def _format_value(value):

        if isinstance(value, int):
            return str(value)
        if not value:
            return ""
        if isinstance(value, list):
            # explicitly set None values to empty string
            return "[" + ",".join([str(x) if (x is not None) else "" for x in value]) + "]"

        return str(value)