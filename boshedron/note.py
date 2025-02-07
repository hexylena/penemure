import hashlib
import magic
import requests
import time
import tempfile
import shutil
import os
from pydantic_changedetect import ChangeDetectionMixin
from pydantic import BaseModel, Field, PastDatetime
from typing import Annotated
from typing import Optional, Union, Any
import datetime
from zoneinfo import ZoneInfo
import uuid
from .tags import *
from .refs import *
from .table import *
from .util import *
from enum import Enum


class BlockTypes(Enum):
    markdown = 'markdown'
    queryTable = 'query-table'
    queryTableEditable = 'query-table-edit'
    queryKanban = 'query-kanban'
    queryCards = 'query-cards'
    chartTable = 'chart-table'
    chartPie = 'chart-pie'
    chartBar = 'chart-bar'
    chartGantt = 'chart-gantt'
    # only appropriate for form pages. TODO: restrict?
    formNumeric = 'form-numeric'
    formMultipleChoice = 'form-multiple-choice'
    formText = 'form-text'

    def pretty(self):
        return {
            'markdown': 'Markdown',
            'queryTable': 'SQLish Query: Table',
            'queryTableEditable': 'Editable Table',
            'queryKanban': 'SQL Query: 看板',
            'chartTable': 'SQL Query: Table',
            'chartPie': 'SQL Query: Pie Chart',
            'chartBar': 'SQL Query: Bar Chart',
            'chartGantt': 'SQLish Query: Gantt Chart (expects columns url, id, time_start, time_end)',
            'queryCards': 'SQL Query: Cards (expects columns urn, title, blurb)',
            'formNumeric': "(Form) Numeric Input",
            'formMultipleChoice': "(Form) Multiple choice, one per line, prefixed with -. Leave an empty '- ' on the last line for a free text entry.",
            'formText': "(Form) Free Text (Short)",
        }.get(self.name, self.name)

    def chart_type(self):
        return self.name.startswith('chart')

    def query_type(self):
        return self.name.startswith('query')

    @classmethod
    def from_str(cls, s):
        if s in cls.__members__:
            return cls.__members__[s]
        else:
            return {v.value: v for (_, v) in cls.__members__.items()}[s]

class MarkdownBlock(BaseModel):
    contents: str
    author: UniformReference
    type: str = 'markdown'
    # Planning to support transcluding blocks at some point with like
    # urn:boshedron:note:deadbeef#dead-beef-cafe-4096
    id: str = Field(default_factory=lambda : str(uuid.uuid4()))

    created_unix: float = Field(default_factory=lambda : time.time())
    updated_unix: float = Field(default_factory=lambda : time.time())

    model_config = ConfigDict(use_enum_values=True)

    @property
    def created(self):
        return datetime.datetime.fromtimestamp(self.created_unix, ZoneInfo('UTC'))

    @property
    def updated(self):
        return datetime.datetime.fromtimestamp(self.updated_unix, ZoneInfo('UTC'))

    def clean_dict(self, note_urn) -> dict:
        d = self.model_dump()
        d['parent'] = note_urn
        d['author'] = self.author.urn
        d['created'] = self.created
        d['updated'] = self.updated
        return d

    def render(self, oe, path, parent):
        import traceback
        try:
            return self._render(oe, path, parent)
        except Exception as e:
            return f'Error: {e} <details><summary>Traceback</summary><pre>{traceback.format_exc()}</pre></details>'

    def _render(self, oe, path, parent):
        # if isinstance(self.type, str):
        #     self.type = BlockTypes.from_str(self.type)

        a = time.time()
        if self.type == BlockTypes.markdown.value:
            page_content = md(self.contents)
        elif self.type.startswith('query'):
            try:
                res = oe.query(self.contents, via=parent.urn)
            except Exception as e:
                return f"<b>ERROR</b> {self.contents}<br>{e}"

            if self.type == BlockTypes.queryTable.value:
                page_content = render_table(res)
            elif self.type == BlockTypes.queryTableEditable.value:
                page_content = render_table_editable(res)
            elif self.type == BlockTypes.queryKanban.value:
                page_content = render_kanban(res)
            elif self.type == BlockTypes.queryCards.value:
                page_content = render_cards(res)
            else:
                raise NotImplementedError(f"self.type={self.type}")
        elif self.type.startswith('chart'):
            if self.type == BlockTypes.chartTable.value:
                res = oe.query(self.contents, sql=True, via=parent.urn)
                page_content = render_table(res)
            elif self.type == BlockTypes.chartPie.value:
                res = oe.query(self.contents, sql=True, via=parent.urn)
                page_content = render_pie(res)
            elif self.type == BlockTypes.chartBar.value:
                res = oe.query(self.contents, sql=True, via=parent.urn)
                page_content = render_bar(res)
            elif self.type == BlockTypes.chartGantt.value:
                res = oe.query(self.contents, via=parent.urn, sql=False) # non proper sql
                page_content = render_gantt(res)
        else:
            raise NotImplementedError(f"self.type={self.type}")

        page_content = UniformReference.rewrite_urns(page_content, path, oe)
        print('render', self.type, time.time() - a)
        # TODO: something better with author.
        return f'''
            <article class="block">
                <div class="contents">{page_content}</div>
                <!-- <span class="author">{self.author.urn}</span> -->
            </article>
        '''


# This describes the data stored in a StoredThing
class Note(ChangeDetectionMixin, BaseModel):
    title: str
    parents: Optional[list[UniformReference]] = Field(default_factory=lambda: list())
    contents: Optional[list[MarkdownBlock]] = Field(default_factory=list)
    # These must all be enumerated explicitly :|
    tags: list[Tag] = Field(default_factory=list)

    version: Optional[int] = 2
    created_unix: float = Field(default_factory=lambda : time.time())
    updated_unix: float = Field(default_factory=lambda : time.time())

    namespace: Union[str, None] = None
    type: str = 'note'
    attachments: list[Union[Reference, UnresolvedReference, ExternalReference, BlobReference]] = Field(default_factory=list)

    def set_parents(self, parents: list[UniformReference]):
        if parents != self.parents:
            self.model_set_changed("parents", original=self.parents)
            self.parents = parents

    def set_contents(self, contents: list[MarkdownBlock]):
        if contents != self.contents:
            self.model_set_changed("contents", original=self.contents)
            self.contents = contents

    def set_tags(self, tags: list[Tag]):
        if tags != self.tags:
            self.model_set_changed("tags", original=self.tags)
            self.tags = tags

    @property
    def created(self):
        return datetime.datetime.fromtimestamp(self.created_unix, ZoneInfo('UTC'))

    @property
    def updated(self):
        return datetime.datetime.fromtimestamp(self.updated_unix, ZoneInfo('UTC'))

    @property
    def blurb(self):
        text = ''
        for x in self.get_contents():
            if x.type == 'markdown':
                text += x.contents

            if len(text) > 120:
                return text[0:120]
        return text.replace('\n', ' ').replace('\r', ' ')

    def touch(self):
        self.updated_unix = time.time()
        for c in (self.contents or []):
            c.updated_unix = time.time()

    def has_parent(self, urn) -> bool:
        return any([UniformReference.match_string(x.urn, urn)
                    for x in self.get_parents()])

    def get_parents(self) -> list[UniformReference]:
        return self.parents or []

    def get_children(self, own_urn, oe) -> list[UniformReference]:
        # semi-equivalent to oe.query("select id from __all__ where parents like '%own_urn%'")
        kids = []
        for note in oe.search():
            if own_urn in note.thing.data.get_parents():
                kids.append(note)

        return kids

    def resolve_parents(self, oe):
        return [oe.find(parent) for parent in self.get_parents()]

    @property
    def icon(self):
        # if t:= self.get_tag(key='icon'):
        #     return t[0].value_icon()

        if self.type == "project":
            return "📁"
        elif self.type == "task":
            return "📝" # TODO: refactor for accessing via icon render functions.
        elif self.type == "account":
            return "👩‍🦰"
        elif self.type in ('note', 'page'):
            return "📓"
        elif self.type == 'log':
            return "⏰"
        elif self.type == 'file':
            return "📎"
        elif self.type == 'form':
            return "🗳" # force B&W +'\uFE0E'
        else:
            return "?"


    def has_tag(self, key: str):
        return len([tag for tag in self.tags if tag.key == key]) > 0

    def add_tag(self, tag: Tag, unique: bool = False):
        self.touch()
        self.model_set_changed("tags", original=self.tags)
        if unique:
            # Remove any other values of this
            self.tags = [t for t in self.tags if t.key != tag.key]

        self.tags.append(tag)

    def get_tag(self, key: Optional[str] = None, enforce_unique: bool = False) -> Optional[Tag]:
        t = self.get_tags(key)
        if enforce_unique and len(t) > 1:
            raise Exception(f"Non-unique tags for key={key}")
        if len(t) == 0:
            return None

        return t[0]

    def get_tags(self, key: Optional[str] = None, val: Optional[str] = None):
        tags = []
        for t in self.tags:
            if key is not None and t.key != key:
                continue
            if val is not None and t.val != val:
                continue
            tags.append(t)
        return tags

    def get_contents(self) -> list[MarkdownBlock]:
        return self.contents or []

    def get_contributors(self, _oe):
        c = []
        for b in self.get_contents():
            c.append(b.author)
        return set(c)

    def ensure_tag(self, key: str, value: str):
        """
        Simimlar to add_tag, except ensures there cannot be duplicates and
        overwrites when there are. Great for adding an icon tag or a Start Time
        (or similar) where there should only be one.
        """
        self.touch()
        self.model_set_changed("tags", original=self.tags)
        # find a matching tag, generally there should only be ONE with that key.
        t = self.get_tags(key=key)
        if len(t) == 0:
            new_tag = Tag(key=key, val=value)
            self.tags.append(new_tag)
        elif len(t) == 1:
            old_tag = t[0]
            old_tag.val = value
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
                self.touch()
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


    def _fmt_datetime(self, t: Tag, a: Literal['date'] | Literal['time'] | Literal['unix']):
        if a == 'unix':
            return float(str(t.val))

        d = datetime.datetime.fromtimestamp(float(str(t.val)), ZoneInfo("UTC"))
        if a == 'date':
            return d.date()
        elif a == 'time':
            return d.time()

    def start(self, a: Literal['date'] | Literal['time'] | Literal['unix'] = 'date'):
        t = self.get_tag(key='start_date')
        if t is not None:
            return self._fmt_datetime(t, a)

    def end(self, a: Literal['date'] | Literal['time'] | Literal['unix'] = 'date'):
        t = self.get_tag(key='end_date')
        if t is not None:
            return self._fmt_datetime(t, a)

    def log_is_closed(self):
        s = self.get_tag(key='start_date')
        e = self.get_tag(key='end_date')

        return not(s is not None and e is not None)

    def cover_image(self):
        t = self.get_tag(key='cover')
        if t is not None:
            return t.val
