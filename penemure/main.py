from pydantic import BaseModel
import glob
import shutil
from jinja2 import Environment, PackageLoader, select_autoescape
import os
from typing import Optional
from .store import GitJsonFilesBackend, OverlayEngine, WrappedStoredThing
from .note import *
from .refs import BlobReference, ExternalReference, UnresolvedReference, UniformReference

from importlib import resources as impresources
from . import templates


class Penemure(BaseModel):
    title: str = "PENEMURE"
    about: str = 'A project manager'

    # Automatic
    private_key_path: str | None = Field(default_factory=lambda: os.environ.get('PENEMURE_PRIVATE_KEY', None))
    auth_method: str | None = Field(default_factory=lambda: os.environ.get('PENEMURE_AUTH_METHOD', 'Local').lower())
    imgproxy_host: str | None = Field(default_factory=lambda: os.environ.get('PENEMURE_IMGPROXY', None))
    path: str = Field(default_factory=lambda: os.environ.get('PENEMURE_PREFIX', '/'))
    server: str | None = Field(default_factory=lambda: os.environ.get('PENEMURE_SERVER', None)) # e.g. http://localhost:9090 (to be concatenated with 'path')

    # Hmm
    overlayengine: OverlayEngine = None
    backends: list[GitJsonFilesBackend]

    data: dict = Field(default_factory=dict)

    @property
    def real_path(self):
        return ('/' + self.path.lstrip('/').rstrip('/') + '/').replace('//', '/')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print(f'PENEMURE: private key enabled: {self.private_key_path}')
        be = kwargs['backends']
        pk = kwargs.get('private_key_path', self.private_key_path)
        if pk:
            for b in be:
                if b.pubkeys is not None:
                    b._private_key_path = pk
        self.overlayengine = OverlayEngine(backends=be)

    # TODO: all assets.
    def pkg_file(self, path: str):
        inp_file = impresources.files(templates) / path
        with inp_file.open("rt") as f:
            return f.read()

    def load(self):
        return self.overlayengine.load()

    def save(self, fsync=False):
        return self.overlayengine.save(fsync=fsync)

    def apps(self):
        """List registered 'apps'"""
        return self.overlayengine.apps()

    def image(self, path, args=None):
        if self.imgproxy_host:
            p = path.replace('/file/blob/', '').lstrip('/')
            print('image', path)
            if args:
                return f"/imgproxy/insecure/{args}/plain/{p}"
            else:
                return f"/imgproxy/insecure/plain/{p}"
        else:
            return path

    def get_config(self, serving=True):
        # def blobify(b: BlobReference, width='40'):
        #     # return f'<img width="{width}" src="/{prefix}/{b.id.url}{b.ext}">'
        #     img_path = os.path.join('', path, b.id.url + b.ext)
        #     print('img', img_path)
        #     return f'<img width="{width}" src="{img_path}">'

        config = {
            'ExportPrefix': self.real_path,
            'IsServing': serving,
            'Title': self.title,
            'About': self.about,
            'MarkdownBlock': MarkdownBlock,
            'UniformReference': UniformReference,
            'System': UniformReference.from_string('urn:penemure:account:system'),
            'VcsRev': 'deadbeefcafe',
            'data': self.data,
            # Gross.
            'TagTypes': sorted([x.replace('penemure.tags.', '')[:-3] 
                                for x in str(TagV2.__args__[0]).split(' | ')])
        }
        if config['ExportPrefix'] == '//':
            config['ExportPrefix'] = '/'

        # if the server is set, prepend.
        if self.server:
            config['ExportPrefix'] = self.server + config['ExportPrefix']

        kwargs = {
            'penemure': self,
            'oe': self.overlayengine,
            'Config': config,
            'blocktypes': BlockTypes, #'blob': blobify
            'hasattr': hasattr,
            'now': local_now(),
        }
        kwargs['pathed_pages'] = {
            x.thing.data.get_tag('page_path').val: x
            for x in
            self.overlayengine.all_pathed_pages()}
        return kwargs

    def export(self, path, format='html'):
        config = self.get_config(serving=False)

        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        if self.overlayengine is None:
            raise Exception("Should not be reached.")

        env = Environment(
            loader=PackageLoader("penemure", "templates"),
            # TODO: re-enable
            autoescape=select_autoescape(".html")
        )

        # export every note into the output according to templates.
        things = self.overlayengine.all_things()

        if format == 'html':
            for fixed in('search.html', 'fulltext.html', 'redir.html'):
                with open(os.path.join(path, fixed), 'w') as handle:
                    template = env.get_template(fixed)
                    page_content = template.render(notes=things, **config)
                    page_content = UniformReference.rewrite_urns(page_content, self)
                    handle.write(page_content)

        # print(env.list_templates())
        # print(env.join_path('assets/main'))
        for st in things:
            p = os.path.join(path, st.thing.url.replace('.html', '.' + format))
            if not os.path.exists(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p), exist_ok=True)

            requested_template = f"note.{format}"
            if tag := st.thing.data.get_tag(key='template'):
                requested_template = tag.val.replace('.html', '.' + format)

            template = env.get_template(requested_template)
            page_content = template.render(note=st, **config)
            page_content = UniformReference.rewrite_urns(page_content, self)

            with open(p, 'w') as handle:
                handle.write(page_content)

            if st.thing.data.has_tag('page_path'):
                t = st.thing.data.get_tag('page_path')
                if t:
                    p = os.path.join(path, str(t.val) + '.' + format)
                    with open(p, 'w') as handle:
                        handle.write(page_content)

            for (_, att) in st.thing.data.attachments:
                blob = self.overlayengine.find_blob(att)
                p = os.path.join(path, blob.thing.relative_path)
                if not os.path.exists(os.path.dirname(p)):
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                shutil.copy(blob.full_path, p)

            for view in st.thing.data._views:
                requested_template = f"{view}.html"
                template = env.get_template(requested_template)
                page_content = template.render(note=st, **config)
                page_content = UniformReference.rewrite_urns(page_content, self)

                ext = st.thing.data.view_ext(view)
                p = os.path.join(path, 'render', view, st.thing.urn.urn + ext)
                if not os.path.exists(os.path.dirname(p)):
                    os.makedirs(os.path.dirname(p), exist_ok=True)

                with open(p, 'w') as handle:
                    handle.write(page_content)

        # os.makedirs(os.path.join(path, 'assets'), exist_ok=True)
        # TODO: use env resolver to find the files?
        ASSET_DIR = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            '..', 'assets')
        shutil.copytree(ASSET_DIR, os.path.join(path, 'assets'))

    def urn_to_url(self, u: re.Match):
        urn_ref = UniformReference.from_string(u.group(1))
        if urn_ref.urn != u.group(1):
            raise Exception(f"Maybe mis-parsed URN, {urn_ref.urn} != {u.group(1)}")

        if u.group(3) == "title":
            try:
                ref = self.overlayengine.find(urn_ref)
                return ref.thing.html_title # should it be html by default?
            except KeyError:
                return urn_ref.urn
        elif u.group(3) == "txt_title":
            try:
                ref = self.overlayengine.find(urn_ref)
                return ref.thing.txt_title
            except KeyError:
                return urn_ref.urn
        elif u.group(3) == "url":
            try:
                ref = self.overlayengine.find_thing_or_blob(urn_ref)
                return os.path.join(self.real_path, ref.thing.url)
            except KeyError:
                return urn_ref.urn
        elif u.group(3) == "link":
            try:
                ref = self.overlayengine.find(urn_ref)
                url = os.path.join(self.real_path, ref.thing.url)
                return f'<a href="{url}">{ref.thing.html_title}</a>' 
            except KeyError:
                try:
                    ref = self.overlayengine.find_blob(urn_ref)
                    url = os.path.join(self.real_path, ref.thing.url)
                    return f'<a href="{url}">{ref.thing.urn.urn}</a>' 

                except KeyError:
                    return f'<a href="#">{urn_ref.urn}</a>' 
        elif u.group(3) == "embed":
            try:
                ref = self.overlayengine.find_blob(urn_ref)
                url = os.path.join(self.real_path, ref.thing.url)
                fix = self.image(url, args="rs:fill:800")
                return f'<img src="{fix}" />'
            except KeyError:
                try:
                    ref = self.overlayengine.find(urn_ref)
                    url = os.path.join(self.real_path, ref.thing.url)
                    return f'<a href="{url}">{ref.thing.html_title}</a>' 

                except KeyError:
                    return f'<a href="#">Couldn\'t find {urn_ref.urn}</a>' 
        else:
            return urn_ref.urn
