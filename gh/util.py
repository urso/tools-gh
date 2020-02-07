import re
import datetime

timedeltaRegex = re.compile(r'((?P<days>\d+?)d)((?P<hours>\d+?)h)?((?P<minutes>\d+?)m)?((?P<seconds>\d+?)s)?')

def parse_timedelta(delta_str):
    parts = timedeltaRegex.match(delta_str)
    if not parts:
        return
    parts = parts.groupdict()
    params = {}
    for name, param in parts.items():
        if param:
            params[name] = int(param)
    return datetime.timedelta(**params)
