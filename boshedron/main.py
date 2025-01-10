from pydantic import BaseModel
import glob
import shutil
from jinja2 import Environment, PackageLoader, select_autoescape
import os
from .store import FsBackend, OverlayEngine, StoredThing
from .refs import BlobReference, ExternalReference, UnresolvedReference


class Boshedron(BaseModel):
    title: str = "BOSHEDRON"
    about: str = '<b style="color:red">DROP AND RUN</b><br><br>DO NOT USE.'
    overlayengine: OverlayEngine = None
    backends: list[FsBackend]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlayengine = OverlayEngine(backends=kwargs['backends'])

    def export(self, path):
        if not os.path.exists(path):
            os.makedirs(path, exist_ok=True)

        def blobify(b: BlobReference, width='40'):
            return f'<img width="{width}" src="/{path}/{b.id.url}{b.ext}">'

        # export every note into the output according to templates.
        stored = self.overlayengine.all()
        things = [x for x in stored if isinstance(x, StoredThing)]
        for st in things:
            p = os.path.join(path, st.relative_path + '.html')
            if not os.path.exists(os.path.dirname(p)):
                os.makedirs(os.path.dirname(p), exist_ok=True)
            env = Environment(
                loader=PackageLoader("boshedron", "templates"),
                # TODO: re-enable
                autoescape=select_autoescape(".html")
            )

            with open(p, 'w') as handle:
                template = env.get_template(st.data.template)
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
