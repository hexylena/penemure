import zoneinfo
import datetime

def local_now():
    return datetime.datetime.now(zoneinfo.ZoneInfo("localtime"))
