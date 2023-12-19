from markupsafe import Markup
from datetime import datetime


class momentjs(object):
    def __init__(self, timestamp):
        self.timestamp = timestamp

    def render(self, format):
        return Markup(
            "<script>\ndocument.write(moment(\"%s\").%s);\n</script>" %
            (self.timestamp.strftime("%Y-%m-%dT%H:%M:%S"), format)
        )

    def calendar(self):
        return self.render("calendar()")

    # def endOf(self, fmt, fnc):
    #     return self.render("endOf(\"%s\").%s" % fmt, fnc)
