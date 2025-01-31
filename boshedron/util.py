import zoneinfo
import subprocess
import datetime
import os

try:
    LOCAL_ZONE = zoneinfo.ZoneInfo("localtime")
except zoneinfo._common.ZoneInfoNotFoundError:
    if 'TZ' in os.environ:
        LOCAL_ZONE = zoneinfo.ZoneInfo(os.environ['TZ'])
    else:
        LOCAL_ZONE = zoneinfo.ZoneInfo('UTC')

def local_now():
    return datetime.datetime.now(tz=LOCAL_ZONE)

def instance_but_not_subclass(obj, cls):
    return type(obj) is cls

def rebase_path(full_path, base):
    # TODO: there's gotta be a better way.
    full_path = os.path.abspath(full_path)
    full_base = os.path.abspath(base)

    return full_path.replace(full_base, '').lstrip('/')

def subprocess_check_call(*args, **kwargs):
    print(['subprocess', 'check_call'], args, kwargs)
    return subprocess.check_call(*args, **kwargs)

def subprocess_check_output(*args, **kwargs):
    print(['subprocess', 'check_output'], args, kwargs)
    return subprocess.check_output(*args, **kwargs)

def sqlite3_type(val):
    if val is None:
        return None
    if str(type(val)) == "<class 'boshedron.tags.TemplateValue'>":
        return None

    # print(str(type(val)))
    return val
