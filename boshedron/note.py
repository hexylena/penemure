import hashlib
import markdown
import magic
import requests
import tempfile
import shutil
import os
from pydantic import BaseModel, Field, AwareDatetime
from typing import Optional, Union, Any
from datetime import datetime
from zoneinfo import ZoneInfo
import uuid
from .tags import *
from .refs import *




class MarkdownBlock(BaseModel):
    contents: str
    author: UniformReference
    type: str = 'markdown'

    def render(self):
        page_content = markdown.markdown(self.contents, extensions=['pymdownx.superfences'])

        return f'<div class="block"><div class="contents">{page_content}</div><div class="author">{self.author.urn}</div></div>'



# This describes the data stored in a StoredThing
class Note(BaseModel):
    title: str
    parents: Optional[list[str]] = None
    contents: Optional[list[MarkdownBlock]] = None
    tags: list[Union[LifecycleTag, AccountTag, DateTag, DescriptionTag, TextTag, IconTag]] = Field(default_factory=list)
    version: Optional[int] = 2
    created: AwareDatetime = Field(default_factory=lambda : datetime.now().astimezone(ZoneInfo('Europe/Amsterdam')))
    updated: AwareDatetime = Field(default_factory=lambda : datetime.now().astimezone(ZoneInfo('Europe/Amsterdam')))
    namespace: Union[str, None] = None
    type: str = 'note'
    attachments: list[Union[Reference, UnresolvedReference, ExternalReference, BlobReference]] = Field(default_factory=list)

    def touch(self):
        self.updated = datetime.now()

    @property
    def icon(self):
        icon_tag = self.has_tag('icon')
        if len(icon_tag) == 1:
            return icon_tag[0].icon
        else:
            icon_tag = None

        if self.type == "project":
            return "📁"
        elif self.type == "task":
            tag = self.has_tag('status')
            if len(tag) == 1 and isinstance(tag, LifecycleTag):
                return tag.values[0].icon()
        elif self.type == "account":
            return "👩‍🦰"
        elif self.type == 'note':
            return "🗒"
        elif self.type == 'log':
            return "⏰"
        else:
            return "?"


    def has_tag(self, key: str):
        return [tag for tag in self.tags if tag.type == key]

    def ensure_tag(self, key: str, value: str, icon=None):
        # find a matching tag, generally there should only be ONE with that key.
        t = [x for x in self.tags if x.type == key]
        if len(t) == 0:
            new_tag = Tag(type=key, title=key.capitalize(), values=[value])
            if icon:
                new_tag.icon = icon
            self.tags.append(new_tag)
        elif len(t) == 1:
            old_tag = t[0]
            if icon:
                old_tag.icon = icon
            if value not in old_tag.values:
                old_tag.values.append(value)
        else:
            raise Exception("Too many tags")

    def persist_attachments(self, location):
        updated_attachments = []
        for attachment in self.attachments:
            if not isinstance(attachment, UnresolvedReference):
                updated_attachments.append(attachment)
                continue

            # attachments are all stored in file/blob namespace.
            if attachment.remote:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                r = requests.get(attachment.path)
                tmp.write(r.content)
                tmp.close()
                attachment.path = tmp.name

            with open(attachment.path, 'rb') as f:
                file_hash = hashlib.file_digest(f, 'sha256').hexdigest()

            path = os.path.join(location, file_hash)
            if not os.path.exists(os.path.dirname(path)):
                os.makedirs(os.path.dirname(path))
            shutil.copy(attachment.path, path)

            blob = BlobReference(
                id=UniformReference(app='file', namespace='blob', ident=file_hash),
                type=magic.from_file(path, mime=True)
            )
            updated_attachments.append(blob)
        self.attachments = updated_attachments

    @property
    def suggested_ident(self) -> Union[str, None]:
        return None
