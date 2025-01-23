import hashlib
import markdown
import magic
import requests
import tempfile
import shutil
import os
from pydantic import BaseModel, Field, PastDatetime
from typing import Annotated
from typing import Optional, Union, Any
from datetime import datetime
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
    queryKanban = 'query-kanban'
    chartTable = 'chart-table'
    chartPie = 'chart-pie'
    chartGantt = 'chart-gantt'

    def pretty(self):
        return {
            'markdown': 'Markdown',
            'queryTable': 'SQLish Query: Table',
            'queryKanban': 'SQL Query: 看板',
            'chartTable': 'SQL Query: Table',
            'chartPie': 'SQL Query: Pie Chart',
            'chartGantt': 'SQLish Query: Gantt Chart',
        }.get(self.name, self.name)

    def chart_type(self):
        return self.name.startswith('chart')

    def query_type(self):
        return self.name.startswith('query')

    @classmethod
    def from_str(cls, s):
        return {
            'markdown': cls.markdown,
            'query-table': cls.queryTable,
            'query-kanban': cls.queryKanban,
            'chart-table': cls.chartTable,
            'chart-pie': cls.chartPie,
            'chart-gantt': cls.chartGantt
        }[s]

class MarkdownBlock(BaseModel):
    contents: str
    author: UniformReference
    type: str = 'markdown'
    # Planning to support transcluding blocks at some point with like
    # urn:boshedron:note:deadbeef#dead-beef-cafe-4096
    id: str = Field(default_factory=lambda : str(uuid.uuid4()))

    model_config = ConfigDict(use_enum_values=True)

    def render(self, oe, path, parent):
        # if isinstance(self.type, str):
        #     self.type = BlockTypes.from_str(self.type)

        if self.type == BlockTypes.markdown.value:
            extension_configs = {
                # "custom_fences": [
                #     {
                #         'name': 'mermaid',
                #         'class': 'mermaid',
                #         'format': pymdownx.superfences.fence_div_format
                #     }
                # ]
            }
            page_content = markdown.markdown(self.contents, extension_configs=extension_configs, 
                                             extensions=['tables', 'footnotes', 'pymdownx.superfences', 'pymdownx.highlight'])
        elif self.type.startswith('query'):
            try:
                res = oe.query(self.contents, via=parent.urn)
            except Exception as e:
                return f"<b>ERROR</b> {self.contents}<br>{e}"

            if self.type == BlockTypes.queryTable.value:
                page_content = render_table(res)
            elif self.type == BlockTypes.queryKanban.value:
                page_content = render_kanban(res)
            else:
                raise NotImplementedError(f"self.type={self.type}")
        elif self.type.startswith('chart'):
            if self.type == BlockTypes.chartTable.value:
                res = oe.query(self.contents, sql=True, via=parent.urn)
                page_content = render_table(res)
            elif self.type == BlockTypes.chartPie.value:
                res = oe.query(self.contents, sql=True, via=parent.urn)
                page_content = render_pie(res)
            elif self.type == BlockTypes.chartGantt.value:
                res = oe.query(self.contents, via=parent.urn) # non proper sql
                page_content = render_gantt(res)
        else:
            raise NotImplementedError(f"self.type={self.type}")

        page_content = UniformReference.rewrite_urns(page_content, path, oe)
        # TODO: something better with author.
        return f'''
            <article class="block">
                <div class="contents">{page_content}</div>
                <!-- <span class="author">{self.author.urn}</span> -->
            </article>
        '''


# This describes the data stored in a StoredThing
class Note(BaseModel):
    title: str
    parents: Optional[list[UniformReference]] = Field(default_factory=lambda: list())
    contents: Optional[list[MarkdownBlock]] = Field(default_factory=list)
    # These must all be enumerated explicitly :|
    tags: list[Annotated[
        Union[Tag.get_subclasses()],
        Field(discriminator="type")
    ]] = Field(default_factory=list)

    version: Optional[int] = 2
    created: PastDatetime = Field(default_factory=lambda : local_now())
    updated: PastDatetime = Field(default_factory=lambda : local_now())
    namespace: Union[str, None] = None
    type: str = 'note'
    attachments: list[Union[Reference, UnresolvedReference, ExternalReference, BlobReference]] = Field(default_factory=list)


    def touch(self):
        self.updated = local_now()

    def has_parent(self, urn) -> bool:
        return urn in [x.urn for x in self.get_parents()]

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

    def get_lineage(self, oe, d=0):
        res = []
        for p_urn in self.get_parents():
            try:
                p = oe.find(p_urn)
                res_sub = p.thing.data.get_lineage(oe, d = d + 1)
                if len(res_sub) == 0:
                    res.append([p.thing.urn.urn])
                else:
                    for r in res_sub:
                        res.append([p.thing.urn.urn, r])
            except KeyError:
                res.append([p_urn])
        return res

    @property
    def icon(self):
        if t:= self.get_tag(typ='icon'):
            return t[0].value_icon()

        if self.type == "project":
            return "📁"
        elif self.type == "task":
            tag = self.get_tag(typ='status')
            if tag is not None:
                return tag.value_icon()
            return '?'
        elif self.type == "account":
            return "👩‍🦰"
        elif self.type in ('note', 'page'):
            return "🗒"
        elif self.type == 'log':
            return "⏰"
        elif self.type == 'file':
            return "📎"
        else:
            return "?"


    def has_tag(self, key: str):
        return len([tag for tag in self.tags if tag.type == key]) > 0

    def add_tag(self, tag: Tag, unique: bool = False):
        self.touch()
        if unique:
            # Remove any other values of this
            self.tags = [t for t in self.tags if t.type != tag.type]

        self.tags.append(tag)

    def get_tag(self, typ: Optional[str] = None, title: Optional[str] = None, enforce_unique: bool = False) -> Tag:
        t = self.get_tags(typ, title)
        if enforce_unique and len(t) > 1:
            raise Exception(f"Non-unique tags for type={typ} and title={title}: {t}")
        if len(t) == 0:
            return None

        return t[0]

    def get_tags(self, typ: Optional[str] = None, title: Optional[str] = None):
        tags = []
        for t in self.tags:
            if typ is not None and t.type != typ:
                continue
            if title is not None and t.title != title:
                continue
            tags.append(t)
        return tags

    def get_contributors(self, oe):
        c = []
        if self.contents is None:
            return []

        for b in self.contents:
            c.append(b.author)
        return set(c)

    def ensure_tag(self, key: str, value: str):
        """
        Simimlar to add_tag, except ensures there cannot be duplicates and
        overwrites when there are. Great for adding an icon tag or a Start Time
        (or similar) where there should only be one.
        """
        self.touch()
        # find a matching tag, generally there should only be ONE with that key.
        t = self.get_tags(typ=key)
        if len(t) == 0:
            new_tag = Tag(type=key, title=key, value=value)
            self.tags.append(new_tag)
        elif len(t) == 1:
            old_tag = t[0]
            old_tag.value = value
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

    def start_unix(self):
        t = self.get_tag(typ='date', title='Start Date')
        if t is not None and isinstance(t, DateTimeTag):
            return t.value.strftime("%s")

    def start_date(self):
        t = self.get_tag(typ='date', title='Start Date')
        if t is not None and isinstance(t, DateTimeTag):
            return t.value.date()

    def start_time(self):
        t = self.get_tag(typ='date', title='Start Date')
        if t is not None and isinstance(t, DateTimeTag):
            return t.value.time().strftime('%H:%M:%S')

    def end_unix(self):
        t = self.get_tag(typ='date', title='End Date')
        if t is not None and isinstance(t, DateTimeTag):
            return t.value.strftime("%s")

    def end_date(self):
        t = self.get_tag(typ='date', title='End Date')
        if t is not None and isinstance(t, DateTimeTag):
            return t.value.date()

    def end_time(self):
        t = self.get_tag(typ='date', title='End Date')
        if t is not None and isinstance(t, DateTimeTag):
            return t.value.time().strftime('%H:%M:%S')

    def log_is_closed(self):
        s = self.get_tag(typ='date', title='Start Date')
        e = self.get_tag(typ='date', title='End Date')

        return not(s is not None and e is not None)

    def cover_image(self):
        t = self.get_tag(typ='cover')
        if t is not None:
            return t.value
