import hashlib
import requests
import tempfile
import shutil
import os
from pydantic import BaseModel, Field, AwareDatetime
from typing import Optional, Union, Any
from datetime import datetime
from enum import Enum


class LifecycleEnum(str, Enum):
    backlog = 'backlog'
    planning = 'planning'
    inprogress = 'in-progress'
    paused = 'paused'
    done = 'done'
    canceled = 'canceled'


class MarkdownBlock(BaseModel):
    contents: str
    author: str
    type: str = 'markdown'

# TODO: probably should be more capable? URN style?
class Reference(BaseModel):
    id: str

class ExternalReference(BaseModel):
    url: str

class UnresolvedReference(BaseModel):
    path: str
    remote: bool = False


class Tag(BaseModel):
    type: str = 'tag'
    title: str = 'Tag'
    values: list[Any] = Field(default_factory=list)
    icon: Optional[Union[str, Reference, ExternalReference]] = None

class LifecycleTag(Tag):
    values: list[LifecycleEnum] = [LifecycleEnum.backlog]


# This describes the data stored in a StoredThing
class Note(BaseModel):
    title: str
    parents: Optional[list[str]] = None
    contents: Optional[list[MarkdownBlock]] = None
    tags: Optional[list[Tag]] = Field(default_factory=list)
    version: Optional[int] = 2
    created: Optional[AwareDatetime] = None
    updated: Optional[AwareDatetime] = None
    namespace: Union[str, None] = None
    type: str = 'note'
    attachments: list[Union[Reference, UnresolvedReference, ExternalReference]] = Field(default_factory=list)

    def ensure_tag(self, key: str, value: str, icon=None):
        if self.tags is None:
            self.tags = []

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

            updated_attachments.append(Reference(id=os.path.join('file', 'blob', file_hash)))
        self.attachments = updated_attachments

    @property
    def suggested_ident(self) -> Union[str, None]:
        return None
