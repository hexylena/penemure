import zoneinfo
import mimetypes
import markdown
import subprocess
import datetime
import os
import datetime

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
    if str(type(val)) == "<class 'penemure.tags.TemplateValue'>":
        return None

    # print(str(type(val)))
    return val

def ellips(val, l=20):
    if val:
        if len(str(val)) > 20:
            return str(val)[0:20] + '…'
    return val


TRY_FORMATS = [
    '%Y-%m-%d %H:%M:%S.%f%z', 
    '%Y-%m-%d %H:%M:%S%z',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%dT%H:%M:%S.%f%z', 
    '%Y-%m-%dT%H:%M:%S%z',
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d'
]
def get_time(t):
    try:
        return datetime.datetime.fromtimestamp(float(t), tz=zoneinfo.ZoneInfo('UTC'))
    except ValueError:
        pass
    for fmt in TRY_FORMATS:
        try:
            return datetime.datetime.strptime(t, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unparseable time: {t}")

def md(c):
    extension_configs = {
        # "custom_fences": [
        #     {
        #         'name': 'mermaid',
        #         'class': 'mermaid',
        #         'format': pymdownx.superfences.fence_div_format
        #     }
        # ]
    }

    return markdown.markdown(
        c,
        extension_configs=extension_configs,
        extensions=[
            'attr_list',
            'codehilite',
            'footnotes', 
            'markdown_checklist.extension',
            'md_in_html',
            'pymdownx.blocks.details',
            'pymdownx.highlight',
            'pymdownx.magiclink',
            'pymdownx.superfences',
            'pymdownx.tilde',
            'sane_lists',
            'smarty',
            'tables',
        ]
    )


def guess_extension(content_type_header):
    # >>> mimetypes.guess_extension('image/webp')
    # '.webp'
    # >>> mimetypes.guess_type('test.webp')
    # ('image/webp', None)
    # TODO: safety!
    try:
        return mimetypes.guess_extension(content_type_header) or 'bin'
    except KeyError:
        return 'bin'
