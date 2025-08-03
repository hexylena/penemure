from typing import Optional
from pydantic import Field
import csv
from .note import *
from .tags import *
from .util import *
from .sqlish import ResultSet
import requests
import re


class Template(Note):
    type: str = 'template'
    template_tags_v2: list[TemplateTagV2] = Field(default_factory=list)

    def instantiate(self) -> Note:
        data = self.model_dump()
        # TODO: rewrite tags
        # TODO: rewrite author from blocks?
        # data['tags'] = [t.instantiate() for t in self.tags]
        data['tags_v2'] = [realise_tag(t) for t in self.template_tags_v2]
        data['type'] = self.title # TODO: validation
        obj = Note.model_validate(data)
        return obj

    def get_tag_value(self, key, value):
        t = [x for x in self.tags if x.key == key]
        if len(t) > 0:
            return t[0].val.get_tag_value(value)
        return value

    def relevant_tag(self, key) -> Optional[TemplateTagV2]:
        for x in self.template_tags_v2:
            if x.key == key:
                return x


class RssFeed(Note):
    type: str = 'rss'
    _views = ['rss']

    def view_mediatype(self, view):
        return 'application/atom+xml'
        # return 'application/xml'
        # return 'application/rss+xml'


class IcalFeed(Note):
    type: str = 'ical'
    _views = ['ical']

    def view_mediatype(self, view):
        return 'text/calendar'


class DataFeed(Note):
    type: str = 'data'
    _views = ['csv']

    def view_mediatype(self, view):
        return 'text/csv'


class DataForm(Note):
    type: str = 'form'
    _views = ['form']

    def form_submission(self, d, oe, be, account: UniformReference) -> UniformReference:
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
            elif block.type == 'form-multiple-choice':
                columns[i] = ', '.join([x for x in matching_values if len(x) > 0])
            elif block.type == 'form-markdown':
                continue
            else:
                columns[i] = matching_values[0]

            # elif block.type == 'form-text':
            # elif block.type == 'form-single-choice':
            #     columns[i] = matching_values[0]
            # elif block.type == 'form-single-choice':
            #     columns[i] = matching_values[0]
            # else:
            #     raise NotImplementedError(f"No support yet for {block.type}")

        # Must be strings.
        headers = map(str, ['date', 'account'] + headers)
        columns = map(str, [time.time(), account.urn] + columns)

        # Need to persist this somewhere. Blob store?
        if t := self.has_attachment('data'):
            att = oe.find_blob(t)

            with open(att.full_path, 'a') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
                writer.writerow(columns)
            return t
        else:
            urn = UniformReference.new_file_urn(ext='csv')
            blob = StoredBlob(urn=urn)
            # Get the full path
            att = be.save_blob(blob, fsync=False)

            with open(att.full_path, 'w') as csvfile:
                writer = csv.writer(csvfile, delimiter=',', quotechar='"',
                                    quoting=csv.QUOTE_MINIMAL)
                writer.writerow(headers)
                writer.writerow(columns)

            # ensure it gets added to the git staging
            att = be.save_blob(blob, fsync=False)

            self.attachments.append(('data', urn))
            return urn

    def form_responses(self, oe) -> GroupedResultSet:
        if t := self.has_attachment('data'):
            att = oe.find_blob(t)
            with open(att.full_path) as csvfile:
                reader = csv.reader(csvfile, delimiter=',', quotechar='"')
                header = next(reader)
                rows = [row for row in reader]
                rs = ResultSet.build(header, rows, title='Form Data')
        else:
            rs = ResultSet.build([], [], title='Form Data')
        return GroupedResultSet(groups=[rs])

    def render_form(self, oe, path, parent, pen):
        results = ""

        for i, block in enumerate(self.get_contents()):
            if not block.type.startswith('form-'):
                continue
            results += block.render(oe, path, parent, pen, form=True)
        return results

    def persist_results(self, oe, data):
        # create attachment if it doesn't exist
        # get a path to it
        # append a line
        # close.
        pass


class Account(Note):
    type: str = 'account'
    username: str

    @property
    def icon(self):
        for attachment in self.attachments:
            if isinstance(attachment, BlobReference) and attachment.type in ('image/png', 'image/jpeg', 'image/jpg', 'image/webp'):
                return f'<img src="/{attachment.id.url}" alt="avatar" style="width: 1em">'

        if t := self.get_tag(key='icon'):
            return super().icon
        return "👩‍🦰"

    def suggest_urn(self):
        return UniformReference(app=self.type, namespace=self.namespace, ident=self.username)

class AccountGithub(Account):
    namespace: Optional[str] = 'gh'

    def update(self, be):
        # TODO: if the file is too recently updated, don't hit the API again.
        data = requests.get(f'https://api.github.com/users/{self.username}').json()
        self.ensure_tag('icon', data['avatar_url'])
        self.ensure_tag('description', data['bio'])

        req = requests.get(data['avatar_url'])
        ext = guess_extension(req.headers['content-type'])
        att_urn = be.store_blob(file_data=req.content, ext=ext)
        self.attachments.append(('avatar', att_urn))


def ModelFromAttr(data):
    t = data.type if hasattr(data, 'type') else data['type']

    if t == 'account':
        ns = data.namespace if hasattr(data, 'namespace') else data.get('namespace',None)
        if ns == 'gh':
            return AccountGithub
        return Account
    elif t == 'template':
        return Template
    elif t == 'rss':
        return RssFeed
    elif t == 'ical':
        return IcalFeed
    elif t == 'form':
        return DataForm
    elif t == 'data':
        return DataFeed
    else:
        return Note
