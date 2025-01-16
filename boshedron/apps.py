import os
from typing import Optional
from .note import Note, UnresolvedReference
from .mixins import AttachmentMixin
import requests


class Project(Note):
    type: str = 'project'


class Page(Note):
    type: str = 'page'
    page_path: str
    # This is the only special case of an additional hardcoded attribute?


class Task(Note):
    type: str = 'task'


class Log(Note):
    type: str = 'log'
    # Went back and forth again on whether or not to have start/end times baked
    # into this class.
    #
    # I don't think i want that. it'd prevent e.g. tasks from having a
    # start/end time.
    #
    # Instead if it's generic, we can do more useful things.


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
        if t := self.get_tag(typ='icon'):
            # todo: how to handle normal values vs URLs vs URNs?
            return t.value
        return "👩‍🦰"


class AccountGithubDotCom(Account):
    namespace: Optional[str] = 'gh'

    def update(self):
        # TODO: if the file is too recently updated, don't hit the API again.
        data = requests.get(f'https://api.github.com/users/{self.username}').json()
        self.ensure_tag('icon', data['avatar_url'], icon=data['avatar_url'])
        self.ensure_tag('description', data['bio'])
        self.attachments.append(UnresolvedReference(path=data['avatar_url'], remote=True))


def ModelFromAttr(data):
    if data['type'] == 'project':
        return Project
    elif data['type'] == 'log':
        return Log
    elif data['type'] == 'account':
        if data['namespace'] == 'gh':
            return AccountGithubDotCom
        return Account
    elif data['type'] == 'page':
        return Page
    elif data['type'] == 'task':
        return Task
    elif data['type'] == 'file':
        if data['namespace'] == 'meta':
            return File
        elif data['namespace'] == 's3':
            return File_S3
        else:
            return Note
    else:
        return Note
