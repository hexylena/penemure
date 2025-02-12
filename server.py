from fastapi import FastAPI, HTTPException, Form, Response, Request, UploadFile, Depends
from fastapi.responses import RedirectResponse, FileResponse
import starlette.status as status
from fastapi.staticfiles import StaticFiles
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from penemure.store import *
from penemure.note import Note, MarkdownBlock
from penemure.refs import UniformReference, UnresolvedReference
from penemure.apps import *
from penemure.errr import *
from penemure.main import *
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Tuple, Dict
import os
import sentry_sdk
import copy
import mimetypes


REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub:/home/user/projects/diary/.notes/').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
bos = Boshedron(backends=backends)
oe = bos.overlayengine
oe.load()


tags_metadata = [
    {
        "name": "system",
        "description": "Manage the system itself and it's concept of the external world",
    },
    {
        "name": "view",
        "description": "Render items",
    },
    {
        "name": "mutate",
        "description": "Create/add/update/delete items",
    },
]

app = FastAPI(
    title=bos.title,
    description=bos.about,
    contact={
        "name": "hexylena",
        "url": "https://hexylena.galaxians.org/",
    },
    license_info={
        "name": "EUPL-1.2",
        "url": "https://interoperable-europe.ec.europa.eu/collection/eupl/eupl-text-eupl-12",
    },
    openapi_tags=tags_metadata
)
app.mount("/assets", StaticFiles(directory="assets"), name="static")


if 'SENTRY_SDK' in os.environ:
    sentry_sdk.init(
        dsn=os.environ['SENTRY_SDK'],
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )


env = Environment(
    loader=PackageLoader("penemure", "templates"),
    # TODO: re-enable
    autoescape=select_autoescape(".html")
)

path = ''
# request.scope.get("root_path")

def blobify(b: BlobReference, width='40'):
    return f'<img width="{width}" src="{path}{b.id.url}{b.ext}">'

config = {
    'ExportPrefix': path,
    'IsServing': True,
    'Title': bos.title,
    'About': bos.about,
    'MarkdownBlock': MarkdownBlock,
    'UniformReference': UniformReference,
    'System': UniformReference.from_string('urn:penemure:account:system'),
}

def render_fixed(fixed, note=None, rewrite=True, note_template=None):
    a = time.time()
    template = env.get_template(fixed)
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

    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})

def render_dynamic(st: WrappedStoredThing, requested_template: str = 'note.html'):
    a = time.time()
    if tag := st.thing.data.get_tag(key='template'):
        requested_template = tag.val or requested_template

    template = env.get_template(requested_template)
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(note=st, bos=bos, oe=bos.overlayengine, Config=config, Gn=gn, blob=blobify)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})



@app.get("/reload", tags=['system'])
def reload():
    bos.load()
    return [len(b.data.keys()) for b in oe.backends]

@app.post("/api/sync", tags=['system', 'api'])
def api_sync():
    prev = [len(b.data.keys()) for b in oe.backends]
    bos.save()
    for b in oe.backends:
        b.sync()
    bos.load()
    after = [len(b.data.keys()) for b in oe.backends]
    return {
        name.name: {'before': b, 'after': a}
        for name, b, a in zip(oe.backends, prev, after)
    }

# @app.get("/list")
# def list() -> list[StoredThing]:
#     return oe.all_things()

class BaseFormData(BaseModel):
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
    # attachments: Annotated[UploadFile, File()]
    attachments: Optional[List[UploadFile]] = Field(default_factory=list)

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


def extract_contents(data: BaseFormData | TimeFormData, default_author=None):
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


def download_blob(urn: UniformReference):
    blob = oe.find_blob(urn)
    return FileResponse(blob.full_path)

@app.get("/file/blob/{ident}", response_class=HTMLResponse, tags=['download'])
def download_ident(ident: str):
    u = UniformReference(app='file', namespace='blob', ident=ident)
    return download_blob(u)

@app.get("/download/{urn}", response_class=HTMLResponse, tags=['download'])
def download(urn: str):
    u = UniformReference.from_string(urn)
    return download_blob(u)


@app.get("/new/{template}", response_class=HTMLResponse, tags=['mutate'])
@app.get("/new", response_class=HTMLResponse, tags=['mutate'])
def get_new(template: Optional[str] = None):
    if template is None:
        return render_fixed('new.html')

    if template.startswith('urn:penemure:'):
        # Then they're providing a note ref.
        u = UniformReference.from_string(template)
        orig = oe.find(u)
        return render_fixed('new.html', note_template=orig.thing.data)

    tpl = oe.search(type='template', title=template)
    if len(tpl) > 0:
        # TODO: how to select which template?
        tpl = tpl[0]
        assert isinstance(tpl.thing.data, Template)
        return render_fixed('new.html', note_template=tpl.thing.data.instantiate())
    else:
        return render_fixed('new.html')

@app.post("/new.html", tags=['mutate'])
@app.post("/new", tags=['mutate'])
def save_new(data: Annotated[BaseFormData, Form()]):
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
    be = oe.get_backend(data.backend)
    for att in only_valid_attachments(data.attachments):
        ext = None
        try:
            ext = mimetypes.guess_extension(att.headers['content-type']) or 'bin'
        except KeyError:
            ext = 'bin'
        finally:
            if ext is None:
                ext = 'bin'
        att_urn = UniformReference.new_file_urn(ext=ext.lstrip('.'))
        att_blob = StoredBlob(urn=att_urn)
        # suboptimal for large files probably.
        be.save_blob(att_blob, fsync=False, data=att.file.read())
        obj.attachments.append((att.filename, att_urn))

    res = bos.overlayengine.add(obj, backend=be)
    return RedirectResponse(f"/redir/{res.thing.urn.urn}", status_code=status.HTTP_302_FOUND)


def only_valid_attachments(atts: list[UploadFile] | None) -> list[UploadFile]:
    if atts is None:
        return []
    # Should we be stricter about the size?
    return [
        a for a in atts
        if (a.size and a.size > 0) or (a.filename != '' and a.filename is not None)
    ]

class NewMultiData(BaseModel):
    project: str
    titles: List[str]
    tags: List[Dict[str, str]]
    type: str = 'task'
    backend: str

@app.post("/new/multi", tags=['mutate'])
def save_new_multi(data: NewMultiData):
    res = []
    be = bos.overlayengine.get_backend(data.backend)

    for (title, tags) in zip(data.titles, data.tags):
        n = Note(title=title, type=data.type)
        n.parents = [UniformReference.from_string(data.project)]
        n.tags = [Tag(key=k, val=v) for (k, v) in tags.items()]
        r = bos.overlayengine.add(n, backend=be)
        res.append(r.thing.urn.urn)
    return res

@app.post("/edit/{urn}", tags=['mutate'])
def save_edit(urn: str, data: Annotated[BaseFormData, Form(media_type="multipart/form-data")]):
    u = UniformReference.from_string(urn)
    orig = oe.find(u)
    orig.thing.data.title = data.title
    orig.thing.data.type = data.type
    orig.thing.data.set_contents(extract_contents(data))

    if isinstance(data.project, str):
        orig.thing.data.set_parents([UniformReference.from_string(data.project)])
    elif data.project is not None:
        orig.thing.data.set_parents([UniformReference.from_string(x) for x in data.project])

    if data.type == 'template' or isinstance(orig.thing.data, Template):
        orig.thing.data.tags = [
                TemplateTag.model_validate({'key': k, 'val': json.loads(v)})
                for (k, v) in zip(data.tag_key, data.tag_val)]
    else:
        orig.thing.data.tags = [Tag(key=k, val=v) for (k, v) in zip(data.tag_key, data.tag_val)]

    be = oe.get_backend(data.backend)
    for att in only_valid_attachments(data.attachments):
        # >>> mimetypes.guess_extension('image/webp')
        # '.webp'
        # >>> mimetypes.guess_type('test.webp')
        # ('image/webp', None)
        # TODO: safety!
        ext = None
        try:
            ext = mimetypes.guess_extension(att.headers['content-type']) or 'bin'
        except KeyError:
            ext = 'bin'
        finally:
            if ext is None:
                ext = 'bin'
        att_urn = UniformReference.new_file_urn(ext=ext.lstrip('.'))
        att_blob = StoredBlob(urn=att_urn)
        # suboptimal for large files probably.
        be.save_blob(att_blob, fsync=False, data=att.file.read())
        orig.thing.data.attachments.append((att.filename, att_urn))
        # print(att_urn)
        # print(att)
        # UploadFile(filename='23-06_Bristol_Stool_Chart.webp', size=90964, headers=Headers({'content-disposition': 'form-data; name="attachments"; filename="23-06_Bristol_Stool_Chart.webp"', 'content-type': 'image/webp'}))
        # urn = UniformReference.new_file_urn(ext='csv')
        # att = StoredBlob(urn=urn)
        # data = '\t'.join(headers) + '\n' + '\t'.join(columns) + '\n'
        # be.save_blob(att, fsync=False, data=data.encode('utf-8'))

    oe.save_thing(orig, fsync=False)
    if be != orig.backend.name:
        oe.migrate_backend_thing(orig, be)

    orig.thing.data.touch()
    return RedirectResponse(f"/redir/{urn}", status_code=status.HTTP_302_FOUND)

@app.get("/delete_question/{urn}", tags=['mutate'])
def delete_question(urn: str):
    a = time.time()
    u = UniformReference.from_string(urn)
    try:
        thing = oe.find(u)
    except KeyError:
        return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)

    template = env.get_template('delete.html')
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(oe=bos.overlayengine, Config=config, Gn=gn, note=thing)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})


@app.get("/delete/{urn}", tags=['mutate'])
def delete(urn: str):
    u = UniformReference.from_string(urn)
    try:
        thing = oe.find(u)
    except KeyError:
        return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)

    orig = thing
    orig.backend.remove_item(orig.thing)
    return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)


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

@app.patch("/time", tags=['mutate'])
def patch_time(data: Annotated[PatchTimeFormData, Form()]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)
    log.thing.data.ensure_tag(key='start_date', value=str(data.start_unix))
    log.thing.data.ensure_tag(key='end_date', value=str(data.end_unix))
    oe.save_thing(log, fsync=False)
    return log

@app.post("/time/continue", tags=['mutate'])
def patch_time(data: Annotated[PatchTimeFormData, Form()]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)

    # Copy title, parents only
    new_log = Note(title=log.thing.data.title, type='log')
    new_log = bos.overlayengine.add(new_log, backend=log.backend)
    new_log.thing.data.set_parents(copy.copy(log.thing.data.parents))
    new_log.thing.data.ensure_tag(key='start_date', value=str(time.time()))
    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)


@app.post("/time.html", tags=['mutate'])
@app.post("/time", tags=['mutate'])
def save_time(data: Annotated[TimeFormData, Form()]):
    if data.urn:
        u = UniformReference.from_string(data.urn)
        log = oe.find(u)
    else:
        log = Note(title=data.title, type='log')
        be = bos.overlayengine.get_backend(data.backend)
        log = bos.overlayengine.add(log, backend=be)

    log.thing.data.touch()
    log.thing.data.set_contents(extract_contents(data))
    log.thing.data.ensure_tag(key='start_date', value=str(data.start_unix))
    new_parents = (data.project or [])
    if new_parents:
        log.thing.data.set_parents([UniformReference.from_string(p) for p in new_parents])
    if data.end_unix:
        log.thing.data.ensure_tag(key='end_date', value=str(data.end_unix))
    bos.overlayengine.save_thing(log)

    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)

@app.exception_handler(404)
def custom_404_handler(_, res):
    a = time.time()
    template = env.get_template('404.html')
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(oe=bos.overlayengine, Config=config, Gn=gn, error=res.detail)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})


@app.get("/search.html", response_class=HTMLResponse, tags=['view'])
@app.get("/search", response_class=HTMLResponse, tags=['view'])
@app.get("/redir.html", response_class=HTMLResponse, tags=['view'])
@app.get("/redir", response_class=HTMLResponse, tags=['view'])
@app.get("/new", response_class=HTMLResponse, tags=['view'])
@app.get("/time", response_class=HTMLResponse, tags=['view'])
@app.get("/sync", response_class=HTMLResponse, tags=['view'])
@app.get("/review", response_class=HTMLResponse, tags=['view'])
def fixed_page_list(request: Request):
    page = request.url.path.lstrip('/').replace('.html', '')
    return render_fixed(page + '.html')

@app.get("/{page}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{page}", response_class=HTMLResponse, tags=['view'])
@app.get("/", response_class=HTMLResponse, tags=['view'])
def index(page=None):
    if page is None:
        page = 'index'

    # We can re-order {page}.html to come after, and then it seems like 'last
    # matching wins', but that's terrible.
    page = page.replace('.html', '')

    # try and find an index page
    for x in oe.all_things():
        if x.thing.data.type == 'page':
            if x.thing.data.has_tag('page_path') and \
               x.thing.data.get_tag('page_path').val == page:
                return render_dynamic(x)
    raise HTTPException(status_code=404, detail="Item not found")


@app.get("/edit/{backend}/{urn}", response_class=HTMLResponse, tags=['mutate'])
def edit_get(backend: str, urn: str):
    u = UniformReference.from_string(urn)
    be = oe.get_backend(backend)
    note = oe.find_thing_from_backend(u, be)
    return render_fixed('edit.html', note, rewrite=False)

@app.get("/edit/{urn}", response_class=HTMLResponse, tags=['mutate'])
def edit_get(urn: str):
    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return render_fixed('edit.html', note, rewrite=False)


@app.get("/redir/note/{urn}", response_class=HTMLResponse, tags=['view'])
@app.post("/redir/note/{urn}", response_class=HTMLResponse, tags=['view'])
@app.get("/redir/{urn}", response_class=HTMLResponse, tags=['view'])
@app.post("/redir/{urn}", response_class=HTMLResponse, tags=['view'])
def redir(urn: str):
    urn = urn.replace('.html', '')
    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return RedirectResponse('/' + note.thing.url, status_code=status.HTTP_302_FOUND)


@app.post("/form/{urn}", response_class=HTMLResponse, tags=['form'])
async def post_form(urn: str, request: Request):
    # TODO: enable auth'd responses
    account = 'urn:penemure:account:system-form'

    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Form not found")

    async with request.form() as form:
        assert isinstance(note.thing.data, DataForm)
        blob_id = note.thing.data.form_submission(form.multi_items(), oe, note.backend, account)
        # Save changes to the note itself.
        blob = oe.find_blob(blob_id)
        blob.save(fsync=False)
        note.save(fsync=False)
        return render_fixed('thanks.html', note=note)


@app.get("/form/{urn}", response_class=HTMLResponse, tags=['form'])
def get_form(urn: str):
    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")

    return render_dynamic(note, requested_template='form.html')


# Eww.
@app.get("/{_app}/{b}/{c}/{d}/{e}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}/{c}/{d}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}/{c}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}/{c}/{d}/{e}", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}/{c}/{d}", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}/{c}", response_class=HTMLResponse, tags=['view'])
@app.get("/{_app}/{b}", response_class=HTMLResponse, tags=['view'])
def read_items(_app, b, c=None, d=None, e=None):
    # _app is intentionally ignored.
    p2 = '/'.join([x for x in (c, d, e) if x is not None and x != ''])
    p = ['urn', 'penemure', 'note', b, p2]
    p = [x for x in p if x is not None and x != '']
    u = ':'.join(p)
    if u.endswith('.html'):
        u = u[0:-5]

    print(u)

    try:
        note = oe.find_thing(u)
        if note is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return render_dynamic(note)
    except OnlyNonBlobs:
        blob = oe.find(u)
        path = oe.get_path(blob)
        with open(path, 'rb') as handle:
            # TODO: blob types
            return Response(content=handle.read(), media_type='image/png')

    except KeyError:
        raise HTTPException(status_code=404, detail=f"URN {u} not found")

@app.get('/manifest.json', tags=['view'])
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


@app.get('/sitesearch.xml', tags=['view'])
def search():
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
