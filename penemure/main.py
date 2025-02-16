from pydantic import BaseModel
import glob
import shutil
from jinja2 import Environment, PackageLoader, select_autoescape
import os
from typing import Optional
from .store import GitJsonFilesBackend, OverlayEngine, WrappedStoredThing
from .note import *
from .refs import BlobReference, ExternalReference, UnresolvedReference, UniformReference


class Penemure(BaseModel):
    title: str = "PENEMURE"
    about: str = 'A project manager'
    private_key_path: str | None = Field(default_factory=lambda: os.environ.get('PENEMURE_PRIVATE_KEY', None))

    overlayengine: OverlayEngine = None
    backends: list[GitJsonFilesBackend]

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

    def load(self):
        return self.overlayengine.load()

    def save(self, fsync=False):
        return self.overlayengine.save(fsync=fsync)

    def apps(self):
        """List registered 'apps'"""
        return self.overlayengine.apps()

    def get_config(self, path, serving=True):
        # def blobify(b: BlobReference, width='40'):
        #     # return f'<img width="{width}" src="/{prefix}/{b.id.url}{b.ext}">'
        #     img_path = os.path.join('', path, b.id.url + b.ext)
        #     print('img', img_path)
        #     return f'<img width="{width}" src="{img_path}">'

        config = {
            'ExportPrefix': '/' + path.lstrip('/').rstrip('/') + '/',
            'IsServing': serving,
            'Title': self.title,
            'About': self.about,
            'MarkdownBlock': MarkdownBlock,
            'UniformReference': UniformReference,
            'System': UniformReference.from_string('urn:penemure:account:system'),
            'VcsRev': 'deadbeefcafe',
        }
        if config['ExportPrefix'] == '//':
            config['ExportPrefix'] = '/'

        kwargs = {'penemure': self, 'oe': self.overlayengine, 'Config': config,
                  'blocktypes': BlockTypes, #'blob': blobify
                  }
        kwargs['pathed_pages'] = {
            x.thing.data.get_tag('page_path').val: x
            for x in
            self.overlayengine.all_pathed_pages()}
        return kwargs

    def export(self, path, format='html', prefix='project-management'):
        config = self.get_config(path=prefix, serving=False)

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
            for fixed in('search.html', ):
                with open(os.path.join(path, fixed), 'w') as handle:
                    template = env.get_template(fixed)
                    page_content = template.render(notes=things, **config)
                    page_content = UniformReference.rewrite_urns(page_content, config['Config']['ExportPrefix'], self.overlayengine)
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
            page_content = UniformReference.rewrite_urns(page_content, config['Config']['ExportPrefix'], self.overlayengine)

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

        os.makedirs(os.path.join(path, 'assets'), exist_ok=True)
        # TODO: use env resolver to find the files?
        for file in glob.glob("assets/*"):
            shutil.copy(file, os.path.join(path, 'assets'))
