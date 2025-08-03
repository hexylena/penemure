from fastapi import FastAPI, HTTPException, Form, Response, Request, UploadFile
from functools import cache
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.responses import StreamingResponse
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
from penemure.tags import *
from penemure.main import *
from typing import List, Dict
import os
import sentry_sdk
import copy
import sqlglot
import requests


import fastapi
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

LOGS = []
STARTED = time.time()

def log(logger, message, **kwargs):
    LOGS.append({'time': datetime.datetime.now(), 
                 'logger': logger, 'message': message, 'kwargs': kwargs})

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub:/home/user/projects/diary/.notes/').split(':')
pen = Penemure.discover(REPOS)
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

FastAPIInstrumentor.instrument_app(app)


ICONS = [
    {
        "purpose": "maskable",
        "sizes": "1462x1462",
        "src": "/assets/maskable_icon.png",
        "type": "image/png"
    },
    {
        "purpose": "maskable",
        "sizes": "96x96",
        "src": "/assets/maskable_icon_x96.png",
        "type": "image/png"
    },
    {
        "purpose": "maskable",
        "sizes": "512x512",
        "src": "/assets/maskable_icon_x512.png",
        "type": "image/png"
    },
    {
        "src":   "/assets/favicon@1024.png",
        "type":  "image/png",
        "sizes": "1024x1024",
    }, {
        "src":   "/assets/favicon@64.png",
        "type":  "image/png",
        "sizes": "64x64",
    }, {
        "src":   "/assets/favicon@256.png",
        "type":  "image/png",
        "sizes": "256x256",
    }
]

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

config = pen.get_config() # Serve at /
path = config['Config']['ExportPrefix']
# request.scope.get("root_path")

if pen.auth_method == 'tailscale':
    security = TailscaleHeaderAuthentication()
elif pen.auth_method == 'remoteuser':
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
        acc = oe.search(type='account', namespace=namespace, username=username)
        if len(acc) >= 1:
            return acc[0]
        else:
            acc = Account(title=name, username=username, namespace=namespace)
            return oe.add(acc, urn=acc.suggest_urn())


def get_current_username(credentials: Annotated[PenemureCredentials, Depends(security)],) -> Optional[WrappedStoredThing]:
    if credentials and credentials.username:
        acc = locate_account(credentials.username, credentials.name, credentials.namespace)
        return acc
    else:
        return None


@app.get("/users/me")
def read_current_user(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    return {"username": username}


def render_fixed(fixed: str, request: Request, note=None, rewrite=True, note_template=None, username=None, **kwargs2):
    a = time.time()
    template = env.get_template(fixed)

    kwargs = pen.get_config()
    if note is not None:
        kwargs['note'] = note

    if note_template is not None:
        kwargs['template'] = note_template

    for k, v in kwargs2.items():
        kwargs[k] = v

    page_content = template.render(**kwargs, username=username)
    if rewrite:
        page_content = UniformReference.rewrite_urns(page_content, pen)

    log('render_fixed', f'Rendered {fixed} in {time.time() - a} for {request.client.host}')
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})

def render_dynamic(st: WrappedStoredThing, requested_template: str | None = None, username=None, media_type: Optional[str]=None):
    a = time.time()
    use_template = 'note.html'
    if tag := st.thing.data.get_tag(key='template'):
        assert isinstance(tag, TextTag)
        use_template = tag.val
    elif requested_template is not None:
        use_template = requested_template

    template = env.get_template(use_template)
    page_content = template.render(note=st, **pen.get_config(), username=username)
    page_content = UniformReference.rewrite_urns(page_content, pen)

    render_kw = {'headers': {'X-Response-Time': str(time.time() - a)}}
    if media_type is not None:
        render_kw['media_type'] = media_type

    log('render_dynamic', f'Rendered {st.thing.urn.urn}#link in {time.time() - a}')
    return HTMLResponse(page_content, **render_kw)

def render_object(thing, template: str, username=None, media_type: Optional[str]=None):
    a = time.time()
    t = env.get_template(template)
    page_content = t.render(thing=thing, **pen.get_config(), username=username)
    page_content = UniformReference.rewrite_urns(page_content, pen)

    render_kw = {'headers': {'X-Response-Time': str(time.time() - a)}}
    if media_type is not None:
        render_kw['media_type'] = media_type

    log('render_object', f'Rendered {thing} in {time.time() - a}')
    return HTMLResponse(page_content, **render_kw)


@app.get("/reload", tags=['system'])
def reload(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    pen.load()
    return [len(b.data.keys()) for b in oe.backends]

@app.post("/api/sync", tags=['system', 'api'])
def api_sync(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    prev = [len(b.data.keys()) for b in oe.backends]
    pen.save()
    for b in oe.backends:
        for line in b.sync(log):
            log('sync', line)
    pen.load()
    log('system.reload', line)
    after = [len(b.data.keys()) for b in oe.backends]
    return {
        name.name: {'before': b, 'after': a}
        for name, b, a in zip(oe.backends, prev, after)
    }


@app.get("/api/view/{backend}/{urn}", tags=['api'])
def api_view_backend(backend: str, urn: str, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(urn.replace('.html', ''))
    if backend != '*':
        be = oe.get_backend(backend)
        note = oe.find_thing_from_backend(u, backend=be)
    else:
        note = oe.find_thing(u)
    return note.thing

@app.get('/api/dump_db')
def dump_db():
    return pen.overlayengine.make_a_db()

# @app.get("/list")
# def list() -> list[StoredThing]:
#     return oe.all_things()

@app.get('/manifest.json', tags=['view'])
def manifest():
    # why the fuck
    title = pen.title.replace('"', '”')
    man = {
        "background_color": "#f80000",
        # TODO: better san
        "name":             title,
        "description":      pen.about.replace('"', '”'),
        "display":          "standalone",
        "scope":            '/', # TODO: make this configurable
        "icons":            ICONS,
        "start_url":        '/', # TODO
        "theme_color":      "#f80000",
        "share_target": {
          "action": "/save",
          "method": "POST",
          "enctype": "multipart/form-data",
          "params": {
              "title": "title",
              "text": "text",
              "url": "link"
          }
        },
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
    # tag_key: List[str] = Field(default_factory=list)
    # tag_val: List[str] = Field(default_factory=list)
    tag_v2_typ: List[str] = Field(default_factory=list)
    tag_v2_key: List[str] = Field(default_factory=list)
    tag_v2_val: List[str] = Field(default_factory=list)

    backend: str
    # attachments: Annotated[UploadFile, File()]
    attachments: Optional[List[UploadFile]] = Field(default_factory=list)


def NoteFromForm(data: BaseFormData, backend, username: Optional[WrappedStoredThing], source=None) -> Note:
    d = data.model_dump()


    # d['tags'] = []
    # for k, v in zip(data.tag_key, data.tag_val):
    #     if k == '' and v == '':
    #         continue
    #
    #     if data.type == 'template':
    #         d['tags'].append({
    #             'key': k,
    #             'val': json.loads(v)
    #         })
    #     else:
    #         d['tags'].append({
    #             'key': k,
    #             'val': v
    #         })

    d['tags_v2'] = []
    template = oe.get_template(data.type)
    for k, v, t in zip(data.tag_v2_key, data.tag_v2_val, data.tag_v2_typ):
        print(k, v, t)
        if k == '' and v == '':
            continue

        tpl_tag = None
        if template:
            tpl_tag = template.thing.data.relevant_tag(k)

        if not tpl_tag:
            # TODO: not this.
            tpl_tag = eval(t + 'TemplateTag')
        print(tpl_tag)

        if data.type == 'template':
            # This should be a BaseTemplateTag class
            #
            # So we expect the value field to have a json rep of that
            vv = json.loads(v)
            # Minus the key which is separated.
            vv['key'] = k
            if tpl_tag:
                vv['typ'] = t
                vv['val'] = tpl_tag.parse_val(vv['val'])
            d['tags_v2'].append(vv)
        else:
            vv = {'key': k}
            if tpl_tag:
                vv['typ'] = t
                vv['val'] = tpl_tag.parse_val(v)

            d['tags_v2'].append(vv)

    # del d['tag_key']
    # del d['tag_val']
    del d['tag_v2_key']
    del d['tag_v2_val']
    del d['tag_v2_typ']

    # We just don't handle attachments here at all.
    d['attachments'] = []
    for att in only_valid_attachments(data.attachments):
        assert att.filename is not None
        ext = guess_extension(att.headers['content-type'])
        att_urn = backend.store_blob(file_data=att.file.read(), ext=ext)
        d['attachments'].append((att.filename, att_urn))

    if isinstance(data.project, str):
        d['parents'] = [UniformReference.from_string(data.project)]
    elif data.project is not None:
        d['parents'] = [UniformReference.from_string(x) for x in data.project]

    del d['project']

    d['contents'] = extract_contents(data, username=username, original=None)

    del d['content_author']
    del d['content_note']
    del d['content_type']
    del d['content_uuid']

    if source:
        s = source.model_dump()

        # Overwrite with our new items.
        for k, v in d.items():
            s[k] = v
        return ModelFromAttr(s).model_validate(s)
    else:
        if 'account' not in d['type']:
            # Only apply to Account, AccountGithub
            d['username'] = None
            d['namespace'] = None
        else:
            raise Exception("Creating a new account via UI not supported")

    return ModelFromAttr(d).model_validate(d)


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
                     username: Optional[WrappedStoredThing],
                     original: List[MarkdownBlock] | None=None):
    res = []
    orig = {}
    if original is not None:
        orig = {
            b.id: b
            for b in original}

    for (t, u, n) in zip(data.content_type, data.content_uuid, data.content_note):

        if t.startswith('chart') or t.startswith('query'):
            try:
                n = oe.fmt_query(n)
            except sqlglot.errors.ParseError:
                # User error
                pass


        if u == 'REPLACEME':
            u = str(uuid.uuid4())

        if u in orig and orig[u].contents == n and orig[u].type == t:
            res.append(orig[u])
        else:
            res.append(MarkdownBlock.model_validate({
                'contents': n,
                'author': username.thing.urn if username else UniformReference(app='account'),
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
def get_new(request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)], template: Optional[str] = None):
    if template is None:
        return render_fixed('new.html', request, username=username)

    # Duplicating
    if template.startswith('urn:penemure:'):
        u = UniformReference.from_string(template)
        tpl = oe.find(u)
        # We could pre-duplicate this? But then it doesn't behave like 'new',
        # it behaves like copy+edit which may violate expectations.
        print('note', tpl.thing.data)
        print('note_template', tpl.thing.data)
        return render_fixed('new.html', request,
                            note=tpl.thing.data,
                            note_template=tpl.thing.data, username=username)

    # From a proper template
    tpl = oe.search(type='template', title=template)
    if len(tpl) > 0:
        # TODO: how to select which template?
        tpl = tpl[0]
        assert isinstance(tpl.thing.data, Template)

        print('note', tpl.thing.data.instantiate())
        print('note_template', tpl.thing.data)
        return render_fixed('new.html', request,
                            note=tpl.thing.data.instantiate(),
                            note_template=tpl.thing.data, username=username)
    else:
        return render_fixed('new.html', request, username=username)

@app.post("/new.html", tags=['mutate'])
@app.post("/new", tags=['mutate'])
def save_new(data: Annotated[BaseFormData, Form()], username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    be = oe.get_backend(data.backend)
    obj = NoteFromForm(data, be, username=username)
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
              username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    be = oe.get_backend(data.backend)
    u = UniformReference.from_string(urn)
    orig = oe.find(u)

    new_note = NoteFromForm(data, be, username=username, source=orig.thing.data)

    # print('orig', orig.thing.data.tags_v2)
    # print('new ', new_note.tags_v2)
    # 1/0
    orig.thing.data.title = new_note.title
    orig.thing.data.type = new_note.type
    # We don't use new_note.contents because this is smarter.
    orig.thing.data.set_contents(extract_contents(data, username, orig.thing.data.contents))

    orig.thing.data.set_parents(new_note.parents)
    orig.thing.data.tags = new_note.tags
    orig.thing.data.tags_v2 = new_note.tags_v2
    # union.
    merged_atts = orig.thing.data.attachments + new_note.attachments
    ma = {v: (k, v) for (k, v) in merged_atts}
    orig.thing.data.attachments = list(ma.values())

    thing = oe.save_thing(orig, fsync=False)
    if be != orig.backend.name:
        oe.migrate_backend_thing(orig, be)

    orig.thing.data.touch()

    return RedirectResponse(os.path.join(path, thing.thing.url), status_code=status.HTTP_302_FOUND)

@app.get("/delete_question/{urn}", tags=['mutate'])
def delete_question(urn: str, request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    a = time.time()
    u = UniformReference.from_string(urn)
    try:
        thing = oe.find(u)
    except KeyError:
        return RedirectResponse(f"/", status_code=status.HTTP_302_FOUND)

    return render_fixed('delete.html', request, username=username, note=thing)


@app.get("/delete/{urn}", tags=['mutate'])
def delete(urn: str, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
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
def patch_time(data: Annotated[PatchTimeFormData, Form()], username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)
    try:
        log.thing.data.ensure_tag(PastDateTimeTag(key='start_date', val=float(data.start_unix)))
    except:
        pass

    try:
        log.thing.data.ensure_tag(PastDateTimeTag(key='end_date', val=float(data.end_unix)))
    except:
        pass

    oe.save_thing(log, fsync=False)
    return log

class PatchNoteContentsData(BaseModel):
    urn: str
    block: str
    contents: str

@app.patch("/patch/block", tags=['patch'])
def patch_note(data: Annotated[PatchNoteContentsData, Form()], username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)
    print(u)
    found = False
    for block in log.thing.data.contents:
        if str(block.id) == data.block:
            block.contents = data.contents
            block.author = username
            found = True
            print(block)

    if not found:
        raise Exception("Couldn't find a matching block")
    log.thing.data.touch(blocks=False)
    oe.save_thing(log, fsync=False)
    return log.thing.data


def _last_end():
    logs = oe.search(type='log')
    max_end_date = max((
        log.thing.data.end('unix') 
        for log in logs if log.thing.data.end('unix')
    ))
    return max_end_date

@app.post("/time/continue/since", tags=['mutate'])
def continue_time(data: Annotated[PatchTimeFormData, Form()], username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)

    # Copy title, parents only
    new_log = Note(title=log.thing.data.title, type='log')
    new_log = pen.overlayengine.add(new_log, backend=log.backend)
    new_log.thing.data.set_parents(copy.copy(log.thing.data.parents) or [])
    new_log.thing.data.ensure_tag(PastDateTimeTag(key='start_date', val=_last_end()))
    new_log.thing.data.add_empty_markdown_if_empty(author=username)
    # Right, have to save after adding tags...
    new_log.save()

    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)

@app.post("/time/continue", tags=['mutate'])
def continue_time(data: Annotated[PatchTimeFormData, Form()], username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(data.urn)
    log = oe.find(u)

    # Copy title, parents only
    new_log = Note(title=log.thing.data.title, type='log')
    new_log = pen.overlayengine.add(new_log, backend=log.backend)
    new_log.thing.data.set_parents(copy.copy(log.thing.data.parents) or [])
    new_log.thing.data.ensure_tag(PastDateTimeTag(key='start_date', val=time.time()))
    new_log.thing.data.add_empty_markdown_if_empty(author=username)
    # Right, have to save after adding tags...
    new_log.save()

    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)


@app.get("/redir/note/{urn}", response_class=HTMLResponse, tags=['view'])
@app.post("/redir/note/{urn}", response_class=HTMLResponse, tags=['view'])
@app.get("/redir/{urn}", response_class=HTMLResponse, tags=['view'])
@app.post("/redir/{urn}", response_class=HTMLResponse, tags=['view'])
def redir(urn: str):
    urn = urn.replace('.html', '')
    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return RedirectResponse(os.path.join(path, note.thing.url), status_code=status.HTTP_302_FOUND)



@app.post("/time.html", tags=['mutate'])
@app.post("/time", tags=['mutate'])
def save_time(data: Annotated[TimeFormData, Form()],
              username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    return _save_time(data, username)


@app.post("/time-since", tags=['mutate'])
def save_time_since(data: Annotated[TimeFormData, Form()],
                    username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    return _save_time(data, username, start_override=_last_end())


@app.post("/time-end", tags=['mutate'])
def save_time_since(data: Annotated[TimeFormData, Form()],
                    username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    return _save_time(data, username, start_override=_last_end(), end_override=int(time.time()))

def _save_time(data: Annotated[TimeFormData, Form()],
              username: Annotated[WrappedStoredThing | None, Depends(get_current_username)],
              start_override: Optional[int] = None,
              end_override: Optional[int] = None):
    if data.urn:
        u = UniformReference.from_string(data.urn)
        log = oe.find(u)
    else:
        log = Note(title=data.title, type='log')
        be = pen.overlayengine.get_backend(data.backend)
        log = pen.overlayengine.add(log, backend=be)

    log.thing.data.touch()
    log.thing.data.title = data.title
    log.thing.data.set_contents(extract_contents(data, username, log.thing.data.contents))
    log.thing.data.add_empty_markdown_if_empty(author=username)

    log.thing.data.ensure_tag(PastDateTimeTag(key='start_date', 
                                              val=start_override if start_override else data.start_unix))
    if end_override:
        log.thing.data.ensure_tag(PastDateTimeTag(key='end_date', 
                                                  val=end_override))
    new_parents = (data.project or [])
    if new_parents:
        log.thing.data.set_parents([UniformReference.from_string(p) for p in new_parents])
    if data.end_unix:
        log.thing.data.ensure_tag(PastDateTimeTag(key='end_date', val=data.end_unix))
    pen.overlayengine.save_thing(log)

    return RedirectResponse(f"/time", status_code=status.HTTP_302_FOUND)


@app.exception_handler(404)
def custom_404_handler(_, res):
    a = time.time()
    template = env.get_template('404.html')
    page_content = template.render(error=res.detail, **pen.get_config())
    page_content = UniformReference.rewrite_urns(page_content, pen)
    return HTMLResponse(page_content, headers={'X-Response-Time': str(time.time() - a)})


# http://image:8080/imgproxy/insecure/rs:fill:800:400/plain/c04331cd-b033-4ea8-9962-81c19c1e8d1e.png
@app.get("/imgproxy/{path_params:path}")
def imgproxy(request: Request, path_params: str = ""):
    # TODO: sign urls
    if not pen.imgproxy_host:
        raise Exception("IMGPROXY not enabled")

    headers = {k: v for k, v in request.headers.items()}
    headers.pop('host')
    headers.pop('accept-encoding')

    url = f'{pen.imgproxy_host}/{path_params}'
    res = requests.get(url, params=request.query_params,
                       headers=headers, stream=True)
    return StreamingResponse(
        res.iter_content(chunk_size=4096),
        status_code=res.status_code,
        headers=headers,
    )


@app.get("/redir.html", response_class=HTMLResponse, tags=['redir'])
@app.get("/search.html", response_class=HTMLResponse, tags=['view'])
@app.get("/fulltext.html", response_class=HTMLResponse, tags=['view'])
@app.get("/search", response_class=HTMLResponse, tags=['view'])
@app.get("/new", response_class=HTMLResponse, tags=['view'])
@app.get("/icon", response_class=HTMLResponse, tags=['view'])
@app.get("/time", response_class=HTMLResponse, tags=['view'])
@app.get("/sync", response_class=HTMLResponse, tags=['view'])
@app.get("/review", response_class=HTMLResponse, tags=['view'])
def fixed_page_list(request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    page = request.url.path.lstrip('/').replace('.html', '')
    return render_fixed(page + '.html', request, username=username)

@app.get("/{page}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{page}", response_class=HTMLResponse, tags=['view'])
@app.get("/", response_class=HTMLResponse, tags=['view'])
def index(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)], page=None):
    if page is None:
        page = 'index'

    # We can re-order {page}.html to come after, and then it seems like 'last
    # matching wins', but that's terrible.
    page = page.replace('.html', '')

    # try and find an index page
    config = pen.get_config()
    if page in config['pathed_pages']:
        return render_dynamic(config['pathed_pages'][page], username=username)
    raise HTTPException(status_code=404, detail="Item not found")

class PatchNoteAttachments(BaseModel):
    note: str
    atts: str
    action: str
    identifier_old: str
    identifier_new: Optional[str] = None

@app.patch("/note/atts", tags=['mutate'])
def patch_note_atts(data: Annotated[PatchNoteAttachments, Form()],
                    username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
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
def edit_get(backend: str, urn: str, request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    be = oe.get_backend(backend)
    note = oe.find_thing_from_backend(u, be)
    return render_fixed('edit.html', request, note, rewrite=False, username=username)

@app.get("/edit/{urn}", response_class=HTMLResponse, tags=['mutate'])
def edit_get_nobe(urn: str, request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return render_fixed('edit.html', request, note, rewrite=False, username=username)

async def get_body(request: Request):
    content_type = request.headers.get('Content-Type')
    if content_type is None:
        raise HTTPException(status_code=400, detail='No Content-Type provided!')
    elif (content_type == 'application/x-www-form-urlencoded' or
          content_type.startswith('multipart/form-data')):
        try:
            return await request.form()
        except Exception:
            raise HTTPException(status_code=400, detail='Invalid Form data')
    else:
        raise HTTPException(status_code=400, detail='Content-Type not supported!')


@app.post("/form/{urn}", response_class=HTMLResponse, tags=['form'])
async def post_form(urn: str, request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)], body=Depends(get_body)):
    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Form not found")

    if username is None:
        raise HTTPException(status_code=403, detail="Authentication required")

    #with request.form() as form:
    form =body
    if True:
        assert isinstance(note.thing.data, DataForm)
        blob_id = note.thing.data.form_submission(form.multi_items(), oe, note.backend, username.thing.urn)
        # Save changes to the note itself.
        blob = oe.find_blob(blob_id)
        blob.save(fsync=False)
        note.save(fsync=False)
        return render_fixed('thanks.html', request,note=note, username=username)


@app.get("/form/{urn}", response_class=HTMLResponse, tags=['form'])
def get_form(urn: str, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")

    return render_dynamic(note, requested_template='form.html', username=username)

@app.get('/form/{urn}/manifest.json', tags=['view'])
def form_manifest(urn):
    u = UniformReference.from_string(urn)
    try:
        note = oe.find_thing(u)
    except KeyError:
        raise HTTPException(status_code=404, detail="Item not found")

    title = note.thing.data.title.replace('"', '”')
    man = {
        "background_color": "#f80000",
        # TODO: better san
        "name":             title,
        "description":      "A form",
        "display":          "standalone",
        "scope":            f'/form/{urn}',
        "icons":            ICONS,
        "start_url":        f'/form/{urn}', # TODO
        "theme_color":      "#f80000",
        "shortcuts": [],
    }
    return man


@app.get("/view/{backend}/{urn}.html", response_class=HTMLResponse, tags=['print'])
def view_note(backend: str, urn: str, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    be = oe.get_backend(backend)
    u = UniformReference.from_string(urn)
    note = oe.find_thing_from_backend(u, backend=be)
    return render_dynamic(note, username=username, requested_template='note.html')

@app.get("/view/{backend}", response_class=HTMLResponse, tags=['print'])
@app.get("/view/{backend}.html", response_class=HTMLResponse, tags=['print'])
def view_backend(backend: str, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    try:
        be = oe.get_backend(backend)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Backend not found")
    return render_object(be, 'backend.html', username=username)

@app.get("/render/{view}/{urn}", response_class=HTMLResponse, tags=['print'])
def render_specific_view(view: str, urn: str, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    # Strip extensions
    if '.' in urn:
        urn = urn[:urn.rindex('.')]

    u = UniformReference.from_string(urn)
    note = oe.find_thing(u)
    return render_dynamic(note, username=username, requested_template=f'{view}.html', media_type=note.thing.data.view_mediatype(view))


@app.get("/me/whoami", tags=['self'])
def whoami(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    return {
        'u': username,
        'urn': username.urn,
    }

@app.get("/me/currently", tags=['self'])
def whatamidoing(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]) -> List[str]:
    return [x.thing.urn.urn for x in oe.search(type='log', custom='open')]

@app.get("/me/currently/trailer", response_class=HTMLResponse, tags=['self'])
def whatamidoing(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]) -> str:
    return "\n".join(f"Penemeure: {x.thing.urn.urn}" for x in oe.search(type='log', custom='open'))


@app.get("/server/currently/json", tags=['self'])
def whatamidoing_json():
    return LOGS[-200:]

@app.get("/server/currently", response_class=HTMLResponse, tags=['self'])
def whatamidoing(request: Request, username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):
    # Last 200
    return render_fixed('server.html', request, username=username,
                        logs=LOGS[-200:], uptime=time.time() - STARTED)

# Eww.
@app.get("/{app}/{b}/{c}/{d}/{e}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}/{d}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}.html", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}/{d}/{e}", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}/{d}", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}/{c}", response_class=HTMLResponse, tags=['view'])
@app.get("/{app}/{b}", response_class=HTMLResponse, tags=['view'])
def read_items(username: Annotated[WrappedStoredThing | None, Depends(get_current_username)], 
               app, b, c=None, d=None, e=None):
    raise HTTPException(status_code=404, detail=f"Route being deprecated")

    # _app is intentionally ignored.
    # but why is everything else? I had some good reason for this. escapes me now.
    if app not in ('account', 'accountgithub'):
        app = 'note'

    p2 = '/'.join([x for x in (c, d, e) if x is not None and x != ''])
    p = ['urn', 'penemure', b, p2]
    p = [x for x in p if x is not None and x != '']
    u = ':'.join(p)
    if u.endswith('.html'):
        u = u[0:-5]

    try:
        note = oe.find_thing(u)
        if note is None:
            raise HTTPException(status_code=404, detail="Item not found.")
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


class AndroidShareIntent(BaseModel):
    title: Optional[str] = None
    text: Optional[str] = None
    url: Optional[str] = None

@app.post("/save", tags=['android'])
def android_share(data: Annotated[AndroidShareIntent, Form(media_type="multipart/form-data")],
                  username: Annotated[WrappedStoredThing | None, Depends(get_current_username)]):

    new_note = Note(
        title=data.title or "Untitled",
        tags_v2=[
            TextTag(key="status", val="Uncategorised"),
        ]
    )
    new_note.contents.append(MarkdownBlock(contents=(data.text or ""),
                                           author=username))

    if data.url:
        new_note.tags_v2.append(URLTag(key="status", val=data.url))

    thing = oe.add(new_note, fsync=False)
    edit_url = f'/edit/{thing.thing.urn.urn}'
    return RedirectResponse(edit_url, status_code=status.HTTP_302_FOUND)
