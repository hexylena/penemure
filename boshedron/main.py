from pydantic import BaseModel
import glob
import shutil
from jinja2 import Environment, PackageLoader, select_autoescape
import os
from typing import Optional
from .store import GitJsonFilesBackend, OverlayEngine, WrappedStoredThing
from .note import *
from .refs import BlobReference, ExternalReference, UnresolvedReference, UniformReference


config = {
    'IsServing': False,
    'MarkdownBlock': MarkdownBlock,
    'UniformReference': UniformReference,
    'System': UniformReference.from_string('urn:boshedron:account:system'),
}


class Boshedron(BaseModel):
    title: str = "BOSHEDRON"
    about: str = '<b style="color:red">DROP AND RUN</b><br><br>DO NOT USE.'
    overlayengine: OverlayEngine = None
    backends: list[GitJsonFilesBackend]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlayengine = OverlayEngine(backends=kwargs['backends'])

    def load(self):
        return self.overlayengine.load()

    def save(self, fsync=False):
        return self.overlayengine.save(fsync=fsync)

    def apps(self):
        """List registered 'apps'"""
        return self.overlayengine.apps()

    def export(self, path, format='html'):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        def blobify(b: BlobReference, width='40'):
            return f'<img width="{width}" src="/{path}/{b.id.url}{b.ext}">'

        if self.overlayengine is None:
            raise Exception("Should not be reached.")

        env = Environment(
            loader=PackageLoader("boshedron", "templates"),
            # TODO: re-enable
            autoescape=select_autoescape(".html")
        )

        # export every note into the output according to templates.
        things = self.overlayengine.all_things()

        if format == 'html':
            for fixed in('search.html', 'redir.html'):
                with open(os.path.join(path, fixed), 'w') as handle:
                    template = env.get_template(fixed)
                    config.update({'ExportPrefix': '/' + path, 'IsServing': False, 'Title': self.title, 'About': self.about})
                    gn = {'VcsRev': 'deadbeefcafe'}
                    page_content = template.render(notes=things, oe=self.overlayengine, Config=config, Gn=gn)
                    page_content = UniformReference.rewrite_urns(page_content, '/' + path, self.overlayengine)
                    handle.write(page_content)

        for st in things:
            p = os.path.join(path, st.thing.url)
            if not os.path.exists(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p), exist_ok=True)

            requested_template = f"note.{format}"
            if tag := st.thing.data.get_tag(key='template'):
                requested_template = tag.val.replace('.html', '.' + format)

            template = env.get_template(requested_template)
            config.update({'ExportPrefix': '/' + path, 'IsServing': False, 'Title': self.title, 'About': self.about})
            gn = {'VcsRev': 'deadbeefcafe'}
            page_content = template.render(note=st, oe=self.overlayengine, Config=config, Gn=gn, blob=blobify)
            page_content = UniformReference.rewrite_urns(page_content, '/' + path, self.overlayengine)

            with open(p, 'w') as handle:
                handle.write(page_content)

            if st.thing.data.has_tag('page_path'):
                t = st.thing.data.get_tag('page_path')
                if t:
                    p = os.path.join(path, str(t.val) + '.' + format)
                    with open(p, 'w') as handle:
                        handle.write(page_content)

            # for att in st.thing.data.attachments:
            #     if isinstance(att, ExternalReference) or isinstance(att, UnresolvedReference):
            #         # TODO
            #         continue
            #
            #     blob = self.overlayengine.find(att.id)
            #     out = os.path.join(path, blob.thing.relative_path + att.ext)
            #
            #     if not os.path.exists(os.path.dirname(out)):
            #         os.makedirs(os.path.dirname(out), exist_ok=True)
            #     shutil.copy(self.overlayengine.get_path(blob), out)

        os.makedirs(os.path.join(path, 'assets'), exist_ok=True)
        # TODO: use env resolver to find the file?
        for file in glob.glob("assets/*"):
            shutil.copy(file, os.path.join(path, 'assets'))
