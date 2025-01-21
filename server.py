from fastapi import FastAPI, HTTPException, Form
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from boshedron.store import GitJsonFilesBackend, OverlayEngine, StoredThing
from boshedron.note import Note, MarkdownBlock
from boshedron.tags import LifecycleEnum
from boshedron.refs import UniformReference, UnresolvedReference
from boshedron.apps import *
from boshedron.main import *
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List

app = FastAPI()
app.mount("/assets", StaticFiles(directory="assets"), name="static")

gb1 = GitJsonFilesBackend.discover('/home/user/projects/issues/')
gb2 = GitJsonFilesBackend.discover('./projects/alt')

bos = Boshedron(backends=[gb1, gb2])
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


def render_fixed(fixed):
    template = env.get_template(fixed)
    config = {'ExportPrefix': path, 'IsServing': True, 'Title': bos.title, 'About': bos.about}
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(bos=bos, oe=bos.overlayengine, Config=config, Gn=gn)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content)

def render_dynamic(st: WrappedStoredThing):
    requested_template: str = "note.html"
    if tag := st.thing.data.get_tag(typ='template'):
        requested_template = tag.value or requested_template

    template = env.get_template(requested_template)
    config = {'ExportPrefix': path, 'IsServing': True, 'Title': bos.title, 'About': bos.about}
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(note=st, bos=bos, oe=bos.overlayengine, Config=config, Gn=gn, blob=blobify)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content)


@app.get("/list")
def list() -> list[StoredThing]:
    return oe.all_things()


@app.get("/{page}.html", response_class=HTMLResponse)
def read_items(page: str):
    if page in ('search', 'new', 'time', 'redir', 'edit'):
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

class FormData(BaseModel):
    title: str
    project: str | List[str]
    type: str
    content_type: List[Any]
    content_uuid: List[Any]
    content_note: List[Any]

@app.post("/new.html")
def save_new(data: Annotated[FormData, Form()]):
    dj = {
        'title': data.title,
        'type': data.type,
        'contents': [
            {
                'contents': n,
                'author': {"app":"account","ident":"hexylena"}, # TODO
                'type': t,
                'id': u,
            }
            for (t, u, n) in zip(data.content_type, data.content_uuid, data.content_note)
        ]
    }
    if isinstance(data.project, str):
        dj['parents'] = [UniformReference.from_string(data.project)]
    else:
        dj['parents'] = [UniformReference.from_string(x) for x in data.project]

    obj = ModelFromAttr(dj).model_validate(dj)
    res = bos.overlayengine.add(obj)
    return RedirectResponse(f"web+boshedron:{res.urn.urn}")

@app.exception_handler(404)
async def custom_404_handler(request, _):
    template = env.get_template('404.html')
    config = {'ExportPrefix': path, 'IsServing': True, 'Title': bos.title, 'About': bos.about}
    gn = {'VcsRev': 'deadbeefcafe'}
    page_content = template.render(oe=bos.overlayengine, Config=config, Gn=gn)
    page_content = UniformReference.rewrite_urns(page_content, path, bos.overlayengine)
    return HTMLResponse(page_content)

@app.get("/", response_class=HTMLResponse)
def index():
    # try and find an index page
    index = [x for x in oe.all_things() if isinstance(x.thing.data, Page) and x.thing.data.page_path == 'index']
    if len(index) == 0:
        raise Exception()

    return render_dynamic(index[0])


# Eww.
@app.get("/{a}/{b}/{c}/{d}/{e}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}/{d}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}/{c}.html", response_class=HTMLResponse)
@app.get("/{a}/{b}.html", response_class=HTMLResponse)
def read_items(a=None, b=None, c=None, d=None, e=None):
    p2 = '/'.join([x for x in (c, d, e) if x is not None and x != ''])
    p = ['urn', 'boshedron', a, b, p2]
    p = [x for x in p if x is not None and x != '']
    u = ':'.join(p)
    note = oe.find_thing(u)
    if note is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return render_dynamic(note)
