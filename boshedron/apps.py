from typing import Optional
from pydantic import Field
from .note import *
from .tags import *
from .mixins import AttachmentMixin
import requests


class Template(Note):
    type: str = 'template'
    tags: list[TemplateTag] = Field(default_factory=list)

    def instantiate(self) -> Note:
        data = self.model_dump()
        # TODO: rewrite tags
        # TODO: rewrite author from blocks?
        data['tags'] = [t.instantiate() for t in self.tags]
        data['type'] = self.title # TODO: validation
        obj = Note.model_validate(data)
        return obj

    def get_tag_value(self, key, value):
        t = [x for x in self.tags if x.key == key]
        if len(t) > 0:
            return t[0].val.get_tag_value(value)
        return value


class DataForm(Note):
    type: str = 'form'


class File(Note):
    type: str = 'file'
    namespace: Optional[str] = 'meta'
    # We assume attachments is length = 1.
    # I'm really not sure there's a reason for it to be multiple?


class File_S3(File, AttachmentMixin):
    type: str = 'file'
    namespace: Optional[str] = 's3'


class Account(Note):
    type: str = 'account'
    username: str

    @property
    def icon(self):
        for attachment in self.attachments:
            if isinstance(attachment, BlobReference) and attachment.type in ('image/png', 'image/jpeg', 'image/jpg', 'image/webp'):
                return f'<img src="/{attachment.id.url}" alt="avatar" style="width: 1em">'

        if t := self.get_tag(key='icon'):
            # todo: how to handle normal values vs URLs vs URNs?
            return f'<img src="{t.val}" alt="avatar" style="width: 1em">'
        return "👩‍🦰"


class AccountGithubDotCom(Account):
    namespace: Optional[str] = 'gh'

    def update(self):
        # TODO: if the file is too recently updated, don't hit the API again.
        data = requests.get(f'https://api.github.com/users/{self.username}').json()
        self.ensure_tag('icon', data['avatar_url'])
        self.ensure_tag('description', data['bio'])
        self.attachments.append(UnresolvedReference(path=data['avatar_url'], remote=True))


def ModelFromAttr(data):
    if data['type'] == 'account':
        if data['namespace'] == 'gh':
            return AccountGithubDotCom
        return Account
    elif data['type'] == 'file':
        if data['namespace'] == 'meta':
            return File
        elif data['namespace'] == 's3':
            return File_S3
        else:
            return Note
    elif data['type'] == 'template':
        return Template
    else:
        return Note
