from __future__ import annotations
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
from typing import Optional, Union, Tuple
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
    # Transclude
    transclude = 'transclude'
    # Charts & Graphs
    queryTable = 'query-table'
    queryTableEditable = 'query-table-edit'
    queryKanban = 'query-kanban'
    queryCards = 'query-cards'
    queryMasony = 'query-masony'
    chartTable = 'chart-table'
    chartPie = 'chart-pie'
    chartBar = 'chart-bar'
    chartGantt = 'chart-gantt'
    # only appropriate for form pages. TODO: restrict?
    formMarkdown = 'form-markdown'
    formNumeric = 'form-numeric'
    formMultipleChoice = 'form-multiple-choice'
    formSingleChoice = 'form-single-choice'
    formText = 'form-text'
    formLocalTime = 'form-local-time'

    def pretty(self):
        return {
            'markdown': 'Markdown',
            'transclude': 'Transclude Block',
            'queryTable': 'SQLish Query: Table',
            'queryTableEditable': 'Editable Table',
            'queryKanban': 'SQL Query: 看板',
            'chartTable': 'SQL Query: Table',
            'chartPie': 'SQL Query: Pie Chart',
            'chartBar': 'SQL Query: Bar Chart',
            'chartGantt': 'SQLish Query: Gantt Chart (expects columns url, id, time_start, time_end)',
            'queryCards': 'SQL Query: Cards (expects columns urn, title, blurb)',
            'queryMasony': 'SQL Query: Masonry Layout (expects only urn)',
            'formMarkdown': "(Form) Markdown",
            'formNumeric': "(Form) Numeric Input",
            'formMultipleChoice': "(Form) Multiple choice (checkbox), one per line, prefixed with -. Leave an empty '- ' on the last line for a free text entry.",
            'formSingleChoice': "(Form) Single choice (radio), one per line, prefixed with -. Leave an empty '- ' on the last line for a free text entry.",
            'formText': "(Form) Free Text (Short)",
            'formLocalTime': '(Form) Local Time',
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
    # urn:penemure:note:deadbeef#dead-beef-cafe-4096
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

    def render(self, oe: 'store.OverlayEngine', path, parent, pen: 'main.Penemure', format='html', form=False):
        import traceback
        try:
            return self._render(oe, path, parent, pen, format=format, form=form)
        except Exception as e:
            return f'Error: {e} <details><summary>Traceback</summary><pre>{traceback.format_exc()}</pre></details>'

    def _render(self, oe: 'store.OverlayEngine', path, parent, pen: 'main.Penemure', format='html', form=False):
        if format == 'md':
            if self.type == BlockTypes.markdown.value:
                page_content = self.contents + '\n'
            else:
                page_content = f'```{self.type}\n{self.contents}\n```\n'
                res = oe.query(self.contents, via=parent.urn)
                for group in res.groups:
                    page_content += '\n'
                    page_content += ' | '.join(group.header) + '\n'
                    page_content += ' | '.join([re.sub('.', '-', header) for header in group.header]) + '\n'
                    for row in group.rows:
                        page_content += ' | '.join(map(str, row)) + '\n'
                    page_content += '{' + f': Title="{group.title}"' + '}\n\n'
                # page_content += res

        elif self.type == BlockTypes.markdown.value:
            page_content = pen.md(self.contents)
        elif self.type == BlockTypes.transclude.value:
            # Just allow one, right?
            note_ref, block_ref = self.contents.strip().split('#', 1)
            note = oe.find(note_ref)
            block = [b for b in note.thing.data.contents if b.id == block_ref]
            if len(block) == 0:
                raise Exception("Could not find a matching block")
            block = block[0]
            page_content = f'''
              <div class="transcluded">
                {pen.md(block.contents)}
              </div>
              <a href="/{note.thing.url}#{block.id}"><small>Source</small></a>
            '''
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
            elif self.type == BlockTypes.queryMasony.value:
                page_content = render_masonry(res)
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
        elif self.type.startswith('form-'):
            title = self.contents.split('\n', 1)[0].strip()
            required = title.endswith('*')
            ra = " required " if required else ""

            # if we aren't rendering the form for user consumption, just make
            # it smaller.
            if not form:
                page_content = f'<details><summary>Form Field: {title} ({self.type})</summary><pre>{self.contents}</pre></details>'
            elif self.type == BlockTypes.formMarkdown.value:
                page_content = pen.md(self.contents)
            else:
                frontmatter = "<div class=\"row question\">"
                frontmatter += f'<label class="col-sm-2" for="block-{self.id}">{title}</label>'
                frontmatter += f'<div class="col-sm-10">'
                page_content = ''

                if self.type == BlockTypes.formNumeric.value:
                    page_content += f'<input name="block-{self.id}" type="number" {ra} step="any" class="form-control"/>'
                elif self.type == BlockTypes.formText.value:
                    page_content += f'<input name="block-{self.id}" type="text" {ra} placeholder="{title}..." class="form-control" />'
                elif self.type == BlockTypes.formMultipleChoice.value:
                    options = self.contents.split('\n')[1:]
                    options = [re.sub(r'^-\s*', '', x.strip()) for x in options]
                    for j, option in enumerate(options):
                        if len(option) > 0:
                            page_content += '<div class="form-option">'
                            page_content += f'<input name="block-{self.id}" type="checkbox" value="{option}" id="block-{self.id}-{j}" />'
                            page_content += f'<label for="block-{self.id}-{j}" style="display: inline">{option}</label>'
                            page_content += '</div>'
                        else:
                            page_content += '<div>'
                            page_content += f'<label for="block-{self.id}">Other</label>'
                            page_content += f'<input name="block-{self.id}" type="text" placeholder="Another value..." class="form-control"/>'
                            page_content += '</div>'
                elif self.type == BlockTypes.formSingleChoice.value:
                    options = self.contents.split('\n')[1:]
                    options = [re.sub('^- ', '', x.strip()) for x in options]
                    print(options)
                    for j, option in enumerate(options):
                        page_content += '<div class="form-option">'
                        page_content += f'<input name="block-{self.id}" type="radio" value="{option}" id="block-{self.id}-{j}" />'
                        page_content += f'<label for="block-{self.id}-{j}" style="display: inline">{option}</label>'
                        page_content += '</div>'
                elif self.type == BlockTypes.formLocalTime.value:
                    # Don't wrap it.
                    frontmatter = None
                    page_content += f'<input id="block-{self.id}" name="block-{self.id}" type="hidden" value="" />'
                    page_content += f"""<script>
                        let local_time = new Date(),
                            local_h = local_time.getHours().toString().padStart(2, "0"),
                            local_m = local_time.getMinutes().toString().padStart(2, "0"),
                            local_s = local_time.getSeconds().toString().padStart(2, "0");
                        document.getElementById("block-{self.id}").value = local_h + ":" + local_m + ":" + local_s;
                        </script>
                    """

                else:
                    raise NotImplementedError(f"No support yet for {self.type}")

                if frontmatter:
                    page_content =  frontmatter + page_content + '</div>'
        else:
            raise NotImplementedError(f"self.type={self.type}")

        page_content = UniformReference.rewrite_urns(page_content, pen)

        if format == 'md':
            return page_content + f'\n<!-- {self.author.urn} | {self.id} -->\n'

        # TODO: something better with author.
        return f'''
            <article class="block" id="{self.id}" data-author="{self.author.urn}">
                <div class="contents">{page_content}</div>
            </article>
        '''

# This describes the data stored in a StoredThing
class Note(ChangeDetectionMixin, BaseModel):
    title: str
    parents: list[UniformReference] = Field(default_factory=list)
    contents: list[MarkdownBlock] = Field(default_factory=list)
    # These must all be enumerated explicitly :|
    tags: list[Tag] = Field(default_factory=list)
    tags_v2: list[TagV2] = Field(default_factory=list)

    version: int = 2
    created_unix: float = Field(default_factory=lambda : time.time())
    updated_unix: float = Field(default_factory=lambda : time.time())

    namespace: str | None = None
    type: str = 'note'
    attachments: list[Tuple[str, UniformReference]] = Field(default_factory=list)

    # Available 'views'
    _views = ['print', 'markdown']
    def view_mediatype(self, view):
        return {'print': 'text/html', 'markdown': 'text/plain'}.get(view, 'text/html')

    def view_ext(self, view) -> str:
        return guess_extension(self.view_mediatype(view))

    # prefix_num: int = 0
    #
    # def __init__(self, *args, **kwargs):
    #     super().__init__(*args, **kwargs)
    def add_empty_markdown_if_empty(self, author: UniformReference):
        if len(self.contents) == 0:
            self.contents.append(MarkdownBlock(contents="", author=author))

    def has_attachment(self, identifier) -> Optional[UniformReference]:
        r = [x for (i, x) in self.attachments if i == identifier]
        if len(r) > 0:
            return r[0]

    def set_parents(self, parents: list[UniformReference]):
        if parents != self.parents:
            self.model_set_changed("parents", original=self.parents)
            self.parents = parents

    def set_contents(self, contents: list[MarkdownBlock]):
        if contents != self.contents:
            self.model_set_changed("contents", original=self.contents)
            self.contents = contents

    def set_tags(self, tags: list[TagV2]):
        if tags != self.tags_v2:
            self.model_set_changed("tags", original=self.tags_v2)
            self.tags_v2 = tags

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

    def touch(self, blocks=True):
        self.updated_unix = time.time()
        if blocks:
            for c in (self.contents or []):
                c.updated_unix = time.time()

    def has_parent(self, urn) -> bool:
        return any([UniformReference.match_string(x.urn, urn)
                    for x in self.get_parents()])

    def has_parents(self) -> bool:
        return len(self.parents) > 0

    def get_parents(self) -> list[UniformReference]:
        return self.parents or []

    def get_children(self, own_urn, oe: 'store.OverlayEngine') -> list[UniformReference]:
        # semi-equivalent to oe.query("select id from __all__ where parents like '%own_urn%'")
        kids = []
        for note in oe.search():
            if own_urn in note.thing.data.get_parents():
                kids.append(note)

        return kids

    def resolve_parents(self, oe: 'store.OverlayEngine'):
        return [oe.find(parent) for parent in self.get_parents()]

    @property
    def icon(self):
        if t:= self.get_tag(key='icon'):
            if t.val.startswith('ph-'):
                return f'<i class="ph {t.val}"></i>'
            elif t.val.startswith('hi-'):
                path = t.val[3:].replace('-', '/', 1)
                # TODO: images are bad :(
                return f'<img src="/assets/healthicons/outline/{path}.svg" style="width: 1em" alt="avatar"/>'
            elif t.val.startswith('https://'):
                return f'<img src="{t.val}" style="width: 1em" alt="avatar"/>'
            elif t.val.startswith('http://'):
                return f'<img src="{t.val}" style="width: 1em" alt="avatar"/>'
            return t.val

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


    def has_tag(self, key: str) -> bool:
        return len([tag for tag in self.tags_v2 if tag.key == key]) > 0

    def relevant_tag(self, key) -> Optional[TagV2]:
        for x in self.tags_v2:
            if x.key == key:
                return x

    def add_tag(self, tag: TagV2, unique: bool = False):
        self.touch()
        self.model_set_changed("tags_v2", original=self.tags)
        if unique:
            # Remove any other values of this
            self.tags_v2 = [t for t in self.tags_v2 if t.key != tag.key]

        self.tags_v2.append(tag)

    def get_tag(self, key: Optional[str] = None, enforce_unique: bool = False) -> Optional[TagV2]:
        t = self.get_tags(key)
        if enforce_unique and len(t) > 1:
            raise Exception(f"Non-unique tags for key={key}")
        if len(t) == 0:
            return None

        return t[0]

    def get_tags(self, key: Optional[str] = None, val: Optional[str] = None) -> list[TagV2]:
        tags = []
        for t in self.tags_v2:
            if key is not None and t.key != key:
                continue
            if val is not None and t.val != val:
                continue
            tags.append(t)
        return tags

    def get_contents(self) -> list[MarkdownBlock]:
        return self.contents or []

    def get_form_fields(self) -> list[MarkdownBlock]:
        return [x for x in self.get_contents() 
                if x.type.startswith('form-') and x.type != "form-markdown"]

    def get_contributors(self, oe: 'store.OverlayEngine'):
        c = []
        for b in self.get_contents():
            c.append(b.author)
        return set(c)

    def ensure_tag(self, tag: TagV2) -> None:
        """
        Simimlar to add_tag, except ensures there cannot be duplicates and
        overwrites when there are. Great for adding an icon tag or a Start Time
        (or similar) where there should only be one.
        """
        self.touch()
        self.model_set_changed("tags_v2", original=self.tags_v2)
        # find a matching tag, generally there should only be ONE with that key.
        print(self.tags_v2)
        self.tags_v2 = [x for x in self.tags_v2 if x.key != tag.key] + [tag]
        print(self.tags_v2)

    def _fmt_datetime(self, t: PastDateTimeTag, a: Literal['date'] | Literal['time'] | Literal['unix'] | Literal['datetime']):
        if a == 'unix':
            return t.val
        elif a == 'date':
            return t.datetime.date()
        elif a == 'time':
            return t.datetime.time()
        elif a == 'datetime':
            return t.datetime

    def start(self, a: Literal['date'] | Literal['time'] | Literal['unix'] = 'date'):
        t = self.get_tag(key='start_date')
        if t is not None:
            assert isinstance(t, PastDateTimeTag)
            return self._fmt_datetime(t, a)

    def end(self, a: Literal['date'] | Literal['time'] | Literal['unix'] = 'date'):
        t = self.get_tag(key='end_date')
        if t is not None:
            assert isinstance(t, PastDateTimeTag)
            return self._fmt_datetime(t, a)

    def duration(self):
        s = self._fmt_datetime(self.get_tag(key='start_date'), 'datetime')
        e = self._fmt_datetime(self.get_tag(key='end_date'), 'datetime')
        if s and e:
            return e - s
        else:
            return datetime.timedelta(seconds=0)


        return not(s is not None and e is not None)

    def log_is_closed(self):
        s = self.get_tag(key='start_date')
        e = self.get_tag(key='end_date')

        return not(s is not None and e is not None)

    def cover_image(self, prefix, oe: 'store.OverlayEngine'):
        if t := self.get_tag(key='cover'):
            ref = oe.find_blob(t.val)
            return os.path.join(prefix, ref.thing.url)
