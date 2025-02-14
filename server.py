from fastapi import FastAPI, HTTPException, Form, Response, Request, UploadFile
from functools import cache
from fastapi.responses import RedirectResponse, FileResponse
import starlette.status as status
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from penemure.store import *
from penemure.auth import *
from penemure.note import Note, MarkdownBlock
from penemure.refs import UniformReference
from penemure.apps import *
from penemure.errr import *
from penemure.util import *
from penemure.main import *
from typing import List, Dict
import os
import sentry_sdk
import copy
import mimetypes


REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub:/home/user/projects/diary/.notes/').split(':')
backends = [GitJsonFilesBackend.discover(x) for x in REPOS]
pen = Penemure(backends=backends)
oe = pen.overlayengine
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
    title=pen.title,
    description=pen.about,
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

config = pen.get_config('/') # Serve at /
path = config['Config']['ExportPrefix']
# request.scope.get("root_path")


AUTH_METHOD = os.environ.get('PENEMURE_AUTH_METHOD', 'Local').lower()

if AUTH_METHOD == 'tailscale':
    security = TailscaleHeaderAuthentication()
elif AUTH_METHOD == 'remoteuser':
    # TODO: expose headers?
    security = RemoteUserAuthentication()
else:
    security = LocalUserAuthentication()

@cache
def locate_account(username: str, name: str, namespace: str):
    if username.endswith('@github'):
        user = username.replace('@github', '')
        acc = oe.search(type='account', namespace='gh', username=user)
        if len(acc) >= 1:
            return acc[0]
        # elif len(acc) > 1:
        #     print(len(acc))
        #     for a in acc:
        #         print(a)
        #     raise Exception("Multiple accounts found, due to overlay? BUG! Not your fault.")
        else:
            acc = AccountGithub(title=name, username=user)
            # Fetch profile pic/status/etc.
            acc.update(oe.backends[0])
            return oe.add(acc, urn=acc.suggest_urn())
    else:
        acc = oe.search(type='account', namespace=None, username=username)
        if len(acc) >= 1:
            return acc[0]
        # elif len(acc) > 1:
        #     raise Exception("Multiple accounts found, due to overlay? BUG! Not your fault.")
        else:
            acc = Account(title=name, username=username, namespace=namespace)
            return oe.add(acc, urn=acc.suggest_urn())


def get_current_username(credentials: Annotated[PenemureCredentials, Depends(security)],) -> UniformReference:
    if not credentials.username:
        return UniformReference(app='account', ident='anonymous')
    else:
        return locate_account(credentials.username, credentials.name, credentials.namespace).thing.urn


@app.get("/users/me")
def read_current_user(username: Annotated[UniformReference, Depends(get_current_username)]):
    return {"username": username}


def render_fixed(fixed, note=None, rewrite=True, note_template=None, username=None):
    a = time.time()
    template = env.get_template(fixed)

    kwargs = pen.get_config(path)
    if note is not None:
        kwargs['note'] = note

    if note_template is not None:
        kwargs['template'] = note_template

    page_content = template.render(**kwargs, username=username)
    if rewrite:
        page_content = UniformReference.rewrite_urns(page_content, path, pen.overlayengine)

    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})

def render_dynamic(st: WrappedStoredThing, requested_template: str = 'note.html', username=None):
    a = time.time()
    if tag := st.thing.data.get_tag(key='template'):
        requested_template = tag.val or requested_template

    template = env.get_template(requested_template)
    page_content = template.render(note=st, **pen.get_config(path), username=username)
    page_content = UniformReference.rewrite_urns(page_content, path, pen.overlayengine)
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})



@app.get("/reload", tags=['system'])
def reload(username: Annotated[UniformReference, Depends(get_current_username)]):
    pen.load()
    return [len(b.data.keys()) for b in oe.backends]

@app.post("/api/sync", tags=['system', 'api'])
def api_sync(username: Annotated[UniformReference, Depends(get_current_username)]):
    prev = [len(b.data.keys()) for b in oe.backends]
    pen.save()
    for b in oe.backends:
        b.sync()
    pen.load()
    after = [len(b.data.keys()) for b in oe.backends]
    return {
        name.name: {'before': b, 'after': a}
        for name, b, a in zip(oe.backends, prev, after)
    }

# @app.get("/list")
# def list() -> list[StoredThing]:
#     return oe.all_things()

@app.get('/manifest.json', tags=['view'])
def manifest():
    # why the fuck
    title = pen.title.replace('"', '”')
    man = {
        "background_color": "#ffffff",
        # TODO: better san
        "name":             title,
        "description":      pen.about.replace('"', '”'),
        "display":          "standalone",
        "scope":            '/', # TODO: make this configurable
        "icons":            [{
            "src":   "/assets/favicon@256.png",
            "type":  "image/png",
            "sizes": "256x256",
        }],
        "start_url":        '/', # TODO
        "theme_color":      "#CE3518",
        "shortcuts": [
          {
            "description": "search all notes",
            "name": "Search",
            "short_name": "Search",
            "url": "/search.html"
          },
          {
            "description": "log new times",
            "name": "Time",
            "short_name": "Time",
            "url": "/time"
          },
        ],
    }

    grs = oe.query('SQL select type, count(type) as count from __all__ group by type order by count desc')
    for group in grs.groups:
        for row in group.rows:
            app = row[0] # Don't care about count
            if app == 'time':
                continue
            man['shortcuts'].append({
                "description": f"to {title}",
                "name": f"Add New {app.title()}",
                "short_name": f"+{app.title()}",
                "url": f"/new/{app}/"
            })
    return man



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
    content_type: List[str] = Field(default_factory=list)
    content_uuid: List[str] = Field(default_factory=list)
    content_note: List[str] = Field(default_factory=list)
    content_author: List[str] = Field(default_factory=list)
    backend: str
    start_unix: float = Field(default_factory=lambda: time.time())
    end_unix: Optional[float] = None
    # Default
    type: str = 'log'


def extract_contents(data: BaseFormData | TimeFormData, 
                     username: UniformReference, 
                     original: List[MarkdownBlock] | None=None):
    res = []
    orig = {}
    if original is not None:
        orig = {
            b.id: b
            for b in original}

    for (t, u, n) in zip(data.content_type, data.content_uuid, data.content_note):

        if t.startswith('chart') or t.startswith('query'):
            n = oe.fmt_query(n)

        if u == 'REPLACEME':
            u = str(uuid.uuid4())

        if u in orig and orig[u].contents == n:
            res.append(orig[u])
        else:
            res.append(MarkdownBlock.model_validate({
                'contents': n,
                'author': username,
                'type': BlockTypes.from_str(t),
                'id': u
            }))
    return res


def download_blob(urn: UniformReference):
    blob = oe.find_blob(urn)
    return FileResponse(blob.full_path)

@app.get("/raw/file/blob/{ident}", response_class=HTMLResponse, tags=['download'])
def download_ident_raw(ident: str):
    u = UniformReference(app='file', namespace='blob', ident=ident)
    return download_blob(u)

@app.get("/file/blob/{ident}", response_class=HTMLResponse, tags=['download'])
def download_ident(ident: str):
    # if ident[-4:] in ('.png', 'webp', 'jpeg', '.jpg'):
    # TODO: imgproxy
    #     return

    u = UniformReference(app='file', namespace='blob', ident=ident)
    return download_blob(u)

# /file/blob is preferred so it matches static deployment.
# @app.get("/download/{urn}", response_class=HTMLResponse, tags=['download'])
# def download(urn: str):
#     u = UniformReference.from_string(urn)
#     return download_blob(u)


@app.get("/new/{template}", response_class=HTMLResponse, tags=['mutate'])
@app.get("/new", response_class=HTMLResponse, tags=['mutate'])
def get_new(username: Annotated[UniformReference, Depends(get_current_username)], template: Optional[str] = None):
    if template is None:
        return render_fixed('new.html', username=username)

    if template.startswith('urn:penemure:'):
        # Then they're providing a note ref.
        u = UniformReference.from_string(template)
        orig = oe.find(u)
        return render_fixed('new.html', note_template=orig.thing.data, username=username)

    tpl = oe.search(type='template', title=template)
    if len(tpl) > 0:
        # TODO: how to select which template?
        tpl = tpl[0]
        assert isinstance(tpl.thing.data, Template)
        return render_fixed('new.html', note_template=tpl.thing.data.instantiate(), username=username)
    else:
        return render_fixed('new.html', username=username)

@app.post("/new.html", tags=['mutate'])
@app.post("/new", tags=['mutate'])
def save_new(data: Annotated[BaseFormData, Form()], username: Annotated[UniformReference, Depends(get_current_username)]):
    dj = {
        'title': data.title,
        'type': data.type,
        'contents': extract_contents(data, username, None)
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
        assert att.filename is not None
        ext = guess_extension(att.headers['content-type'])
        att_urn = be.store_blob(file_data=att.file.read(), ext=ext)
        obj.attachments.append((att.filename, att_urn))

    res = pen.overlayengine.add(obj, backend=be)
    # TODO: figure out why note was missing from URL
    return RedirectResponse(os.path.join(path, res.thing.url), status_code=status.HTTP_302_FOUND)


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
    be = pen.overlayengine.get_backend(data.backend)

    # TODO: no authorship of these tracked!
    for (title, tags) in zip(data.titles, data.tags):
        n = Note(title=title, type=data.type)
        n.parents = [UniformReference.from_string(data.project)]
        n.tags = [Tag(key=k, val=v) for (k, v) in tags.items()]
        r = pen.overlayengine.add(n, backend=be)
        res.append(r.thing.urn.urn)
    return res

@app.post("/edit/{urn}", tags=['mutate'])
def save_edit(urn: str, data: Annotated[BaseFormData, Form(media_type="multipart/form-data")],
              username: Annotated[UniformReference, Depends(get_current_username)]):

    u = UniformReference.from_string(urn)
    orig = oe.find(u)
    orig.thing.data.title = data.title
    orig.thing.data.type = data.type
    orig.thing.data.set_contents(extract_contents(data, username, orig.thing.data.contents))

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
        assert att.filename is not None
        ext = guess_extension(att.headers['content-type'])
        att_urn = be.store_blob(file_data=att.file.read(), ext=ext)
        orig.thing.data.attachments.append((att.filename, att_urn))

    thing = oe.save_thing(orig, fsync=False)
    if be != orig.backend.name:
        oe.migrate_backend_thing(orig, be)

    orig.thing.data.touch()
    return RedirectResponse(os.path.join(path, thing.thing.url), status_code=status.HTTP_302_FOUND)

@app.get("/delete_question/{urn}", tags=['mutate'])
def delete_question(urn: str, username: Annotated[UniformReference, Depends(get_current_username)]):
    a = time.time()
    u = UniformReference.from_string(urn)
    try:
        thing = oe.find(u)
    except KeyError:
        return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)

    return render_fixed('delete.html', username=username)


@app.get("/delete/{urn}", tags=['mutate'])
def delete(urn: str, username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    try:
        thing = oe.find(u)
    except KeyError:
        return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)

    orig = thing
    orig.backend.remove_item(orig.thing)
    return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)


class PatchTimeFormData(BaseModel):
    urn: str
    start_unix: float
    end_unix: float

@app.patch("/time", tags=['mutate'])
def patch_time(data: Annotated[PatchTimeFormData, Form()], username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)
    log.thing.data.ensure_tag(key='start_date', value=str(data.start_unix))
    log.thing.data.ensure_tag(key='end_date', value=str(data.end_unix))
    oe.save_thing(log, fsync=False)
    return log

@app.post("/time/continue", tags=['mutate'])
def patch_time(data: Annotated[PatchTimeFormData, Form()], username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)

    # Copy title, parents only
    new_log = Note(title=log.thing.data.title, type='log')
    new_log = pen.overlayengine.add(new_log, backend=log.backend)
    new_log.thing.data.set_parents(copy.copy(log.thing.data.parents) or [])
    new_log.thing.data.ensure_tag(key='start_date', value=str(time.time()))
    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)


@app.post("/time.html", tags=['mutate'])
@app.post("/time", tags=['mutate'])
def save_time(data: Annotated[TimeFormData, Form()],
              username: Annotated[UniformReference, Depends(get_current_username)]):
    if data.urn:
        u = UniformReference.from_string(data.urn)
        log = oe.find(u)
    else:
        log = Note(title=data.title, type='log')
        be = pen.overlayengine.get_backend(data.backend)
        log = pen.overlayengine.add(log, backend=be)

    log.thing.data.touch()
    log.thing.data.set_contents(extract_contents(data, username, log.thing.data.contents))
    log.thing.data.ensure_tag(key='start_date', value=str(data.start_unix))
    new_parents = (data.project or [])
    if new_parents:
        log.thing.data.set_parents([UniformReference.from_string(p) for p in new_parents])
    if data.end_unix:
        log.thing.data.ensure_tag(key='end_date', value=str(data.end_unix))
    pen.overlayengine.save_thing(log)

    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)

@app.exception_handler(404)
def custom_404_handler(_, res):
    a = time.time()
    template = env.get_template('404.html')
    page_content = template.render(error=res.detail, **pen.get_config(path))
    page_content = UniformReference.rewrite_urns(page_content, path, pen.overlayengine)
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})


@app.get("/search.html", response_class=HTMLResponse, tags=['view'])
@app.get("/search", response_class=HTMLResponse, tags=['view'])
@app.get("/new", response_class=HTMLResponse, tags=['view'])
@app.get("/time", response_class=HTMLResponse, tags=['view'])
@app.get("/time", response_class=HTMLResponse, tags=['view'])
@app.get("/sync", response_class=HTMLResponse, tags=['view'])
@app.get("/review", response_class=HTMLResponse, tags=['view'])
def fixed_page_list(request: Request, username: Annotated[UniformReference, Depends(get_current_username)]):
    page = request.url.path.lstrip('/').replace('.html', '')
    return render_fixed(page + '.html', username=username)

@app.get("/{page}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{page}", response_class=HTMLResponse, tags=['view'])
@app.get("/", response_class=HTMLResponse, tags=['view'])
def index(username: Annotated[UniformReference, Depends(get_current_username)], page=None):
    if page is None:
        page = 'index'

    # We can re-order {page}.html to come after, and then it seems like 'last
    # matching wins', but that's terrible.
    page = page.replace('.html', '')

    # try and find an index page
    config = pen.get_config(path)
    if 'index' in config['pathed_pages']:
        return render_dynamic(config['pathed_pages']['index'], username=username)
    raise HTTPException(status_code=404, detail="Item not found")

class PatchNoteAttachments(BaseModel):
    note: str
    atts: str
    action: str
    identifier_old: str
    identifier_new: Optional[str] = None

@app.patch("/note/atts", tags=['mutate'])
def patch_note_atts(data: Annotated[PatchNoteAttachments, Form()],
                    username: Annotated[UniformReference, Depends(get_current_username)]):
    note = oe.find(UniformReference.from_string(data.note))
    atts = UniformReference.from_string(data.atts)

    updated_atts = []
    if data.action == 'rename-blob':
        for (i, ref) in note.thing.data.attachments:
            if data.identifier_old == i and atts == ref:
                updated_atts.append((data.identifier_new, ref))
            else:
                updated_atts.append((i, ref))
    elif data.action == 'detach-blob':
        for (i, ref) in note.thing.data.attachments:
            if data.identifier_old == i and atts == ref:
                continue
            else:
                updated_atts.append((i, ref))
    else:
        raise Exception()

    note.thing.data.attachments = updated_atts
    note.save(fsync=False)
    return RedirectResponse(os.path.join(path, note.thing.url), status_code=status.HTTP_200_OK)


@app.get("/edit/{backend}/{urn}", response_class=HTMLResponse, tags=['mutate'])
def edit_get(backend: str, urn: str, username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    be = oe.get_backend(backend)
    note = oe.find_thing_from_backend(u, be)
    return render_fixed('edit.html', note, rewrite=False, username=username)

@app.get("/edit/{urn}", response_class=HTMLResponse, tags=['mutate'])
def edit_get_nobe(urn: str, username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return render_fixed('edit.html', note, rewrite=False, username=username)


@app.post("/form/{urn}", response_class=HTMLResponse, tags=['form'])
async def post_form(urn: str, request: Request, username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Form not found")

    async with request.form() as form:
        assert isinstance(note.thing.data, DataForm)
        blob_id = note.thing.data.form_submission(form.multi_items(), oe, note.backend, username)
        # Save changes to the note itself.
        blob = oe.find_blob(blob_id)
        blob.save(fsync=False)
        note.save(fsync=False)
        return render_fixed('thanks.html', note=note, username=username)


@app.get("/form/{urn}", response_class=HTMLResponse, tags=['form'])
def get_form(urn: str, username: Annotated[UniformReference, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")

    return render_dynamic(note, requested_template='form.html', username=username)


# Eww.
@app.get("/{app}/{b}/{c}/{d}/{e}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}/{d}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}/{d}/{e}", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}/{d}", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}", response_class=HTMLResponse, tags=['view'])
def read_items(username: Annotated[UniformReference, Depends(get_current_username)], 
               app, b, c=None, d=None, e=None):

    # _app is intentionally ignored.
    if app != 'account':
        app = 'note'

    p2 = '/'.join([x for x in (c, d, e) if x is not None and x != ''])
    p = ['urn', 'penemure', app, b, p2]
    p = [x for x in p if x is not None and x != '']
    u = ':'.join(p)
    if u.endswith('.html'):
        u = u[0:-5]

    try:
        note = oe.find_thing(u)
        if note is None:
            raise HTTPException(status_code=404, detail="Item not found")
        return render_dynamic(note, username=username)
    except OnlyNonBlobs:
        blob = oe.find(u)
        path = oe.get_path(blob)
        with open(path, 'rb') as handle:
            # TODO: blob types
            return Response(content=handle.read(), media_type='image/png')

    except KeyError:
        raise HTTPException(status_code=404, detail=f"URN {u} not found")

@app.get('/sitesearch.xml', tags=['view'])
def search():
    data = f"""<?xml version="1.0"?>
<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/"
                       xmlns:moz="http://www.mozilla.org/2006/browser/search/">
  <ShortName>{pen.title}</ShortName>
  <Description>{pen.about}</Description>
  <InputEncoding>UTF-8</InputEncoding>
  <Image width="16" height="16" type="image/x-icon">/assets/favicon@256.png</Image>
  <Url type="text/html" template="/search.html?q={ '{searchTerms}' }"/>
  <Url type="application/opensearchdescription+xml" rel="self" template="/sitesearch.xml" />
</OpenSearchDescription>
    """
    # <Url type="application/x-suggestions+json" template="[suggestionURL]"/>
    return Response(content=data, media_type="application/opensearchdescription+xml")
