import zoneinfo
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
