from pydantic import BaseModel
import glob
import shutil
from jinja2 import Environment, PackageLoader, select_autoescape
import os
from typing import Optional
from .store import FsBackend, OverlayEngine, StoredThing
from .apps import Page
from .refs import BlobReference, ExternalReference, UnresolvedReference, UniformReference


class Boshedron(BaseModel):
    title: str = "BOSHEDRON"
    about: str = '<b style="color:red">DROP AND RUN</b><br><br>DO NOT USE.'
    overlayengine: OverlayEngine = None
    backends: list[FsBackend]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlayengine = OverlayEngine(backends=kwargs['backends'])

    def load(self):
        return self.overlayengine.load()

    def save(self):
        return self.overlayengine.save()

    def export(self, path):
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
        stored = self.overlayengine.all()
        things = [x for x in stored if isinstance(x, StoredThing)]

        with open(os.path.join(path, 'search.html'), 'w') as handle:
            template = env.get_template('search.html')
            config = {'ExportPrefix': '/' + path, 'IsServing': False, 'Title': self.title, 'About': self.about}
            gn = {'VcsRev': 'deadbeefcafe'}
            page_content = template.render(notes=things, oe=self.overlayengine, Config=config, Gn=gn)
            page_content = UniformReference.rewrite_urns(page_content, '/' + path, self.overlayengine)
            handle.write(page_content)

        for st in things:
            p = os.path.join(path, st.relative_path + '.html')
            if not os.path.exists(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p), exist_ok=True)
            if isinstance(st.data, Page):
                p = os.path.join(path, st.data.page_path + '.html')

            with open(p, 'w') as handle:
                requested_template = "note.html"
                if tag := st.data.get_tag(typ='template'):
                    requested_template = tag.value

                template = env.get_template(requested_template)
                config = {'ExportPrefix': '/' + path, 'IsServing': False, 'Title': self.title, 'About': self.about}
                gn = {'VcsRev': 'deadbeefcafe'}
                handle.write(template.render(note=st, oe=self.overlayengine, Config=config, Gn=gn, blob=blobify))

            for att in st.data.attachments:
                if isinstance(att, ExternalReference) or isinstance(att, UnresolvedReference):
                    # TODO
                    continue

                blob = self.overlayengine.find(att.id)
                out = os.path.join(path, blob.relative_path + att.ext)

                if not os.path.exists(os.path.dirname(out)):
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                shutil.copy(self.overlayengine.get_path(blob), out)

        os.makedirs(os.path.join(path, 'assets'), exist_ok=True)
        for file in glob.glob("assets/*"):
            shutil.copy(file, os.path.join(path, 'assets'))
