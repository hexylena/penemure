from fastapi import FastAPI, HTTPException, Form, Response
from fastapi.responses import RedirectResponse
import starlette.status as status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from boshedron.store import *
from boshedron.note import Note, MarkdownBlock
from boshedron.tags import LifecycleEnum
from boshedron.refs import UniformReference, UnresolvedReference
from boshedron.apps import *
from boshedron.main import *
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List
import os
import sentry_sdk
import copy

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="static")


if 'SENTRY_SDK' in os.environ:
    sentry_sdk.init(
        dsn=os.environ['SENTRY_SDK'],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )


REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub:/home/user/projects/diary/.notes/').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
bos = Boshedron(backends=backends)
oe = bos.overlayengine
oe.load()

env = Environment(
    loader=PackageLoader("boshedron", "templates"),
    # TODO: re-enable
    autoescape=select_autoescape(".html")
)

path = ''
# request.scope.get("root_path")

def blobify(b: BlobReference, width='40'):
    return f'<img width="{width}" src="{path}{b.id.url}{b.ext}">'


def render_fixed(fixed, note=None, rewrite=True, note_template=None):
    template = env.get_template(fixed)
    config = {'ExportPrefix': path, 'IsServing': True, 'Title': bos.title, 'About': bos.about}
    gn = {'VcsRev': 'deadbeefcafe'}
    kwargs = {'bos': bos, 'oe': bos.overlayengine, 'Config': config,
              'Gn': gn, 'blocktypes': BlockTypes}
    if note is not None:
        kwargs['note'] = note

    if note_template is not None:
        kwargs['template'] = note_template

    page_content = template.render(**kwargs)
    if rewrite:
        page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content)

def render_dynamic(st: WrappedStoredThing):
    requested_template: str = "note.html"
    if tag := st.thing.data.get_tag(key='template'):
        requested_template = tag.val or requested_template

    template = env.get_template(requested_template)
    config = {'ExportPrefix': path, 'IsServing': True, 'Title': bos.title, 'About': bos.about}
    gn = {'VcsRev': 'deadbeefcafe'}
    print(repr(st))
    page_content = template.render(note=st, bos=bos, oe=bos.overlayengine, Config=config, Gn=gn, blob=blobify)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content)


@app.get("/reload")
def reload():
    bos.load()
    return [len(b.data.keys()) for b in oe.backends]

@app.get("/sync")
def sync():
    for b in oe.backends:
        b.sync()
    bos.load()
    return [len(b.data.keys()) for b in oe.backends]


# @app.get("/list")
# def list() -> list[StoredThing]:
#     return oe.all_things()

class FormData(BaseModel):
    urn: Optional[str] = None
    title: str
    project: Optional[str | List[str]] = Field(default_factory=list)
    type: str
    content_type: List[str]
    content_uuid: List[str]
    content_note: List[str]
    content_author: List[str]
    tag_key: List[str] = Field(default_factory=list)
    tag_val: List[str] = Field(default_factory=list)
    backend: str

class TimeFormData(BaseModel):
    urn: Optional[str] = None
    title: str
    project: Optional[str | List[str]] = []
    content_type: List[str]
    content_uuid: List[str]
    content_note: List[str]
    content_author: List[str]
    backend: str
    start_unix: int
    end_unix: int


def extract_contents(data: FormData | TimeFormData, default_author=None):
    a2 = None
    if default_author is None:
        a2 = UniformReference.model_validate({"app":"account","ident":"hexylena"}) # TODO
    # else:
    #     a2 = UniformReference.model_validate(a) # TODO

    res = []
    for (t, u, n, a) in zip(data.content_type, data.content_uuid, data.content_note, data.content_author):
        if isinstance(a, str):
            a = UniformReference.from_string(a)

        if t.startswith('chart') or t.startswith('query'):
            n = oe.fmt_query(n)

        if u == 'REPLACEME':
            u = str(uuid.uuid4())

        res.append(MarkdownBlock.model_validate({
            'contents': n,
            'author': a or a2,
            'type': BlockTypes.from_str(t),
            'id': u
        }))
    return res

@app.get("/new/{template}", response_class=HTMLResponse)
@app.get("/new", response_class=HTMLResponse)
def get_new(template: Optional[str] = None):
    if template is None:
        return render_fixed('new.html')

    if template.startswith('urn:boshedron:'):
        # Then they're providing a note ref.
        u = UniformReference.from_string(template)
        orig = narrow_thing(oe.find(u))
        return render_fixed('new.html', note_template=orig.thing.data)

    tpl = oe.search(type='template', title=template)
    if len(tpl) > 0:
        # TODO: how to select which template?
        tpl = tpl[0]
        assert isinstance(tpl.thing.data, Template)
        return render_fixed('new.html', note_template=tpl.thing.data.instantiate())

@app.post("/new.html")
@app.post("/new")
def save_new(data: Annotated[FormData, Form()]):
    dj = {
        'title': data.title,
        'type': data.type,
        'contents': extract_contents(data)
    }
    if data.project is None:
        dj['parents'] = []
    elif isinstance(data.project, str):
        dj['parents'] = [UniformReference.from_string(data.project)]
    else:
        dj['parents'] = [UniformReference.from_string(x) for x in data.project]

    if data.type == 'template':
        dj['tags'] = [
                TemplateTag.model_validate({'key': k, 'val': json.loads(v)})
                for (k, v) in zip(data.tag_key, data.tag_val)]
    else:
        dj['tags'] = [Tag(key=k, val=v) for (k, v) in zip(data.tag_key, data.tag_val)]

    # raise Exception()

    obj = ModelFromAttr(dj).model_validate(dj)
    be = bos.overlayengine.get_backend(data.backend)
    res = bos.overlayengine.add(obj, backend=be)
    return RedirectResponse(f"/redir/{res.thing.urn.urn}", status_code=status.HTTP_302_FOUND)

@app.post("/edit/{urn}")
def save_edit(urn: str, data: Annotated[FormData, Form()]):
    u = UniformReference.from_string(urn)
    orig = narrow_thing(oe.find(u))
    orig.thing.data.title = data.title
    orig.thing.data.type = data.type
    orig.thing.data.contents = extract_contents(data)
    for b in orig.thing.data.contents:
        print(b)

    if isinstance(data.project, str):
        orig.thing.data.parents = [UniformReference.from_string(data.project)]
    elif data.project is not None:
        orig.thing.data.parents = [UniformReference.from_string(x) for x in data.project]

    if data.type == 'template' or isinstance(orig.thing.data, Template):
        orig.thing.data.tags = [
                TemplateTag.model_validate({'key': k, 'val': json.loads(v)})
                for (k, v) in zip(data.tag_key, data.tag_val)]
    else:
        orig.thing.data.tags = [Tag(key=k, val=v) for (k, v) in zip(data.tag_key, data.tag_val)]

    # print(data)
    # raise Exception()

    oe.save_thing(orig, fsync=False)
    be = oe.get_backend(data.backend)
    if be != orig.backend.name:
        oe.migrate_backend_thing(orig, be)

    orig.thing.data.touch()
    return RedirectResponse(f"/redir/{urn}", status_code=status.HTTP_302_FOUND)


class TimeFormData(BaseModel):
    urn: Optional[str] = None
    title: str
    project: Optional[str | List[str]] = []
    content_type: Optional[List[str]] = []
    content_uuid: Optional[List[str]] = []
    content_note: Optional[List[str]] = []
    content_author: Optional[List[str]] = []
    backend: str
    start_unix: float = Field(default_factory=lambda: time.time())
    end_unix: Optional[float] = None
    # Default
    type: str = 'log'

class PatchTimeFormData(BaseModel):
    urn: str
    start_unix: float
    end_unix: float

@app.patch("/time")
def patch_time(data: Annotated[PatchTimeFormData, Form()]):
    u = UniformReference.from_string(data.urn)
    log = narrow_thing(oe.find(u))
    log.thing.data.ensure_tag(key='start_date', value=str(data.start_unix))
    log.thing.data.ensure_tag(key='end_date', value=str(data.end_unix))
    oe.save_thing(log, fsync=False)
    return log

@app.post("/time/continue")
def patch_time(data: Annotated[PatchTimeFormData, Form()]):
    u = UniformReference.from_string(data.urn)
    log = narrow_thing(oe.find(u))

    # Copy title, parents only
    new_log = Note(title=log.thing.data.title, type='log')
    new_log = bos.overlayengine.add(new_log, backend=log.backend)
    new_log.thing.data.parents = copy.copy(log.thing.data.parents)
    new_log.thing.data.ensure_tag(key='start_date', value=str(time.time()))
    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)


@app.post("/time.html")
@app.post("/time")
def save_time(data: Annotated[TimeFormData, Form()]):
    if data.urn:
        u = UniformReference.from_string(data.urn)
        log = narrow_thing(oe.find(u))
    else:
        log = Note(title=data.title, type='log')
        be = bos.overlayengine.get_backend(data.backend)
        log = bos.overlayengine.add(log, backend=be)

    log.thing.data.touch()
    log.thing.data.contents = extract_contents(data)
    log.thing.data.ensure_tag(key='start_date', value=str(data.start_unix))
    if data.end_unix:
        log.thing.data.ensure_tag(key='end_date', value=str(data.end_unix))

    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)

@app.exception_handler(404)
def custom_404_handler(request, res):
    template = env.get_template('404.html')
    config = {'ExportPrefix': path, 'IsServing': True, 'Title': bos.title, 'About': bos.about}
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(oe=bos.overlayengine, Config=config, Gn=gn, error=res.detail)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content)

@app.get("/index.html", response_class=HTMLResponse)
@app.get("/", response_class=HTMLResponse)
def index():
    # try and find an index page
    index = [x for x in oe.all_things() if x.thing.data.type == 'page']
    if len(index) == 0:
        raise Exception()

    return render_dynamic(index[0])

@app.get("/edit/{urn}", response_class=HTMLResponse)
def edit_get(urn: str):
    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return render_fixed('edit.html', note, rewrite=False)


@app.get("/redir/{urn}", response_class=HTMLResponse)
@app.post("/redir/{urn}", response_class=HTMLResponse)
def redir(urn: str):
    u = UniformReference.from_string(urn)
    # note = oe.find_thing(u)
    return RedirectResponse(u.url, status_code=status.HTTP_302_FOUND)


# Eww.
@app.get("/{a}/{b}/{c}/{d}/{e}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}/{d}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}/{d}/{e}", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}/{d}", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}", response_class=HTMLResponse)
@app.get("/{a}/{b}", response_class=HTMLResponse)
def read_items(a=None, b=None, c=None, d=None, e=None):
    p2 = '/'.join([x for x in (c, d, e) if x is not None and x != ''])
    p = ['urn', 'boshedron', a, b, p2]
    p = [x for x in p if x is not None and x != '']
    u = ':'.join(p)
    if u.endswith('.html'):
        u = u[0:-5]

    try:
        note = oe.find_thing(u)
        if note is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return render_dynamic(note)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"URN {u} not found")

@app.get('/manifest.json')
def manifest():
    return {
        "background_color": "#ffffff",
        # TODO: better san
        "name":             bos.title.replace('"', '”'),
        "description":      bos.about.replace('"', '”'),
        "display":          "standalone",
        "scope":            '/', # TODO: make this configurable
        "icons":            [{
            "src":   "/assets/favicon@256.png",
            "type":  "image/png",
            "sizes": "256x256",
        }],
        "start_url":        '/', # TODO
        "theme_color":      "#CE3518",
    }


@app.get('/sitesearch.xml')
def manifest():
    data = f"""<?xml version="1.0"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"
                       xmlns:moz="http://www.mozilla.org/2006/browser/search/">
  <ShortName>{bos.title}</ShortName>
  <Description>{bos.about}</Description>
  <InputEncoding>UTF-8</InputEncoding>
  <Image width="16" height="16" type="image/x-icon">/assets/favicon@256.png</Image>
  <Url type="text/html" template="/search.html?q={ '{searchTerms}' }"/>
  <Url type="application/opensearchdescription+xml" rel="self" template="/sitesearch.xml" />
</OpenSearchDescription>
    """
    # <Url type="application/x-suggestions+json" template="[suggestionURL]"/>
    return Response(content=data, media_type="application/opensearchdescription+xml")


@app.get("/{page}.html", response_class=HTMLResponse)
@app.get("/{page}", response_class=HTMLResponse)
def fixed_page(page: str):
    page = page.replace('.html', '')
    if page in ('search', 'new', 'time', 'redir'):
        return render_fixed(page + '.html')

    return f"""
    <html>
        <head>
            <title>Some HTML in here</title>
        </head>
        <body>
            <h1>Look ma! HTML! {page}</h1>
        </body>
    </html>
    """
