import hashlib
import magic
import requests
import tempfile
import shutil
import os
from pydantic import BaseModel, Field, AwareDatetime
from typing import Optional, Union, Any
from datetime import datetime
from zoneinfo import ZoneInfo
from enum import Enum


class LifecycleEnum(str, Enum):
    backlog = 'backlog'
    planning = 'planning'
    inprogress = 'in-progress'
    blocked = 'blocked'
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

class BlobReference(Reference):
    type: str

    @property
    def ext(self):
        if self.type == 'application/png':
            return '.png'
        return ".xyz"

class ExternalReference(BaseModel):
    url: str

class UnresolvedReference(BaseModel):
    path: str
    remote: bool = False


class Tag(BaseModel):
    # TODO: is there any sane usecase for multi-valued tags that are used everywhere?
    type: str = 'tag'
    title: str = 'Tag'
    values: list[Any] = Field(default_factory=list)
    icon: Optional[Union[str, Reference, BlobReference, ExternalReference]] = None

    @property
    def html_icon(self):
        if self.title == "Status":
            return "🚦"
        elif self.title == "Assignee" or self.title == "assignee":
            return "👤"
        elif self.title == "Author":
            return "👤"
        elif self.title == "Tags":
            return "🏷"
        elif self.title == "Due":
            return "📅"
        elif self.title == "Estimate":
            return "⏱"
        elif self.type == "time":
            return "⏱"
        elif self.title == "Priority":
            return "🔥"
        elif self.title == "Effort":
            return "🏋️"
        elif self.title == "Progress":
            return "📈"
        elif self.title == "Start":
            return "🏁"
        elif self.title == "End":
            return "🏁"
        elif self.title == "Created":
            return "📅"
        elif self.title == "Modified":
            return "📅"
        elif self.title == "Completed":
            return "📅"
        elif self.title == "Blocked":
            return "🚫"
        elif self.title == "Blocking":
            return "🚫"

        return ""

class LifecycleTag(Tag):
    values: list[LifecycleEnum] = [LifecycleEnum.backlog]


# This describes the data stored in a StoredThing
class Note(BaseModel):
    title: str
    parents: Optional[list[str]] = None
    contents: Optional[list[MarkdownBlock]] = None
    tags: Optional[list[Union[Tag, LifecycleTag]]] = Field(default_factory=list)
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
                if tag.values[0] == LifecycleEnum.done:
                    return "✅"
                elif tag.values[0] == LifecycleEnum.inprogress:
                    return "🚧"
                elif tag.values[0] == LifecycleEnum.blocked:
                    return "🚫"
                else:
                    return "📝"
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

            blob = BlobReference(
                id=os.path.join('file', 'blob', file_hash),
                type=magic.from_file(path, mime=True)
            )
            updated_attachments.append(blob)
        self.attachments = updated_attachments

    @property
    def suggested_ident(self) -> Union[str, None]:
        return None
