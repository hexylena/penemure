import os
from pydantic import BaseModel, AwareDatetime
from typing import Optional
from .note import Note, Reference, UnresolvedReference
from .mixins import AttachmentMixin
import requests
from datetime import datetime


class Project(Note):
    type: str = 'project'
    blocking: Optional[list[str]] = None


class Page(Note):
    type: str = 'page'
    page_path: str

    def suggested_ident(self):
        return '../' + self.page_path


class Task(Note):
    type: str = 'task'
    blocking: Optional[list[str]] = None


class Log(Note):
    type: str = 'log'
    start_time: Optional[AwareDatetime] = None
    end_time: Optional[AwareDatetime] = None


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
    sameAs: Optional[list[Reference]] = None

    def suggested_ident(self):
        return self.username

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
