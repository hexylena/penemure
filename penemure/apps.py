from typing import Optional
from pydantic import Field
import csv
from .note import *
from .tags import *
from .sqlish import ResultSet
from .mixins import AttachmentMixin
import requests
import re


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

    def form_submission(self, d, oe, be, account) -> UniformReference:
        columns = [None] * len(self.get_form_fields())
        headers = []

        for i, block in enumerate(self.get_form_fields()):
            key = f'block-{block.id}'

            matching_values = [v for (k, v) in d if k == key]
            title = block.contents.split('\n', 1)[0].strip()
            headers.append(title)
            required = title.endswith('*')

            if required and (len(matching_values) == 0 or matching_values[0] is None or matching_values[0] == ''):
                raise Exception(f"Missing required field {title}")

            if block.type == 'form-numeric':
                columns[i] = float(matching_values[0])
            elif block.type == 'form-text':
                columns[i] = matching_values[0]
            elif block.type == 'form-multiple-choice':
                columns[i] = ', '.join([x for x in matching_values if len(x) > 0])
            elif block.type == 'form-single-choice':
                columns[i] = matching_values[0]
            else:
                raise NotImplementedError(f"No support yet for {block.type}")

        # Must be strings.
        headers = map(str, ['date', 'account'] + headers)
        columns = map(str, [time.time(), account] + columns)

        # Need to persist this somewhere. Blob store?
        if t := self.has_attachment('data'):
            att = oe.find_blob(t)
            with open(att.full_path, 'ab') as handle:
                data = '\t'.join(columns) + '\n'
                handle.write(data.encode('utf-8'))
            return t
        else:
            urn = UniformReference.new_file_urn(ext='csv')
            att = StoredBlob(urn=urn)
            data = '\t'.join(headers) + '\n' + '\t'.join(columns) + '\n'
            be.save_blob(att, fsync=False, data=data.encode('utf-8'))
            self.attachments.append(('data', urn))
            return urn

    def form_responses(self, oe) -> GroupedResultSet:
        if t := self.has_attachment('data'):
            att = oe.find_blob(t)
            with open(att.full_path) as csvfile:
                reader = csv.reader(csvfile, delimiter='\t', quotechar='"')
                header = next(reader)
                rows = [row for row in reader]
                rs = ResultSet.build(header, rows, title='Form Data')
        else:
            rs = ResultSet.build([], [], title='Form Data')
        return GroupedResultSet(groups=[rs])

    def render_form(self, oe, path, parent):
        results = ""

        for i, block in enumerate(self.get_contents()):
            results += block.render(oe, path, parent)
        return results

    def persist_results(self, oe, data):
        # create attachment if it doesn't exist
        # get a path to it
        # append a line
        # close.
        pass

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
    elif data['type'] == 'form':
        return DataForm
    else:
        return Note
