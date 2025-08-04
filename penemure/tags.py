from __future__ import annotations
from pydantic import BaseModel, Field, NaiveDatetime
import itertools
import hashlib
import json
from typing import Literal
from pydantic import ConfigDict
from typing import Optional, Union, Any
import datetime
from zoneinfo import ZoneInfo
from .refs import *
from .util import *
from abc import ABC

FIELD_SEP = chr(0x001E)

# We have two primary places where tags need to be rendered:
# 1. Arbitrarily detached from metadata (f.exs the search page, or, maybe we'll
#    want to render a subset for an e.g. author line)
# 2. With key/values separately, as in a metadata table.
#
# We want to use information from the 'template' tag, in order to render the
# 'real' tag always. E.g. the colour/presentation/title should always be set at
# the level of the template tag, and that applied across the real tags.

def hashed_colour(val):
    m = hashlib.sha256()
    m.update(val.encode('utf-8'))
    m.digest()
    d = int.from_bytes(m.digest()[0:2]) % 360
    x = int.from_bytes(m.digest()[3:5]) % 30
    return f'hsl({d}deg 75% {65 + x}%) !important'

class BaseTemplateTag(BaseModel):
    key: str
    # The rendered title
    title: str
    default: Any
    typ: Literal['UnusedGenericTemplate'] = 'UnusedGenericTemplate'

    @property
    def typ_real(self):
        return self.typ

    @property
    def is_template(self):
        return True

    def get_title(self):
        return self.title or self.key

    def render_key(self, *args, **kwargs):
        return self.title or self.key

    # def render(self, *args, **kwargs):
    #     return f'<span class="template tag">{self.render_key()}={ellips(self)}</span>'

    def render_val(self, *args):
        return f'{ellips(self)}'

    def render_tag(self, template: TextTemplateTag):
        return f'<span class="tag">{self.render_key(template)}={self.render_val(template)}</span>'

    @property
    def val_safe(self):
        return json.dumps(self.model_dump())

    def instantiate_data(self):
        return {'typ': self.typ_real.replace('Template', ''),
                'key': self.key,
                'val': self.default}

    def render_input(self, current_val: Any, oe: 'store.OverlayEngine'):
        return f'<input type="text" name="tag_v2_val" value="{current_val or self.default}" />'

    @classmethod
    def parse_val(cls, val: Any):
        """For 'complex' types that have different UI presentations, bring them back into our space"""
        print('parse_val', cls, val)
        return val


class BaseTag(BaseModel):
    key: str
    val: Any
    typ: Literal['UnusedGeneric'] = 'UnusedGeneric'

    @property
    def is_template(self):
        return False

    # I have decided to ignore these errors for incompatible overriding of
    # method.
    #
    # I understand why they're happening (the subclass is adding restrictions
    # not present on the parent, and things cannot be substituted generically,
    # violating the LSP)
    #
    # But I do not know how to fix that in python. Maybe I'm stupid.
    # 
    # Mainly I just want sane behaviour on the parents (e.g. render_key,
    # render_tag working for the generic case) with the ability to special case
    # as-needed.
    def render_key(self, template: None | BaseTemplateTag):
        if template and isinstance(template, BaseTemplateTag): # At one point being provided a wrappedstoredhting? bad.
            return template.get_title()
        return self.key.title()

    def render_val(self, template: BaseTemplateTag):
        return self.val

    def render_tag(self, template: TextTemplateTag):
        return f'<span class="tag">{self.render_key(template)}={self.render_val(template)}</span>'

    # is OE necessary? Yes, yes it is for ref tags.
    def render_input(self, template: BaseTemplateTag | None, oe: 'store.OverlayEngine'):
        print('render_input', type(template))
        if isinstance(template, BaseTemplateTag):
            return template.render_input(self.val, oe)
        elif isinstance(template, BaseTag):
            return template.render_input(None, oe)

        # if template:
        #     return template.render_input(self.val, oe)

        return f'<input type="text" name="tag_v2_val" value="{self.val or tpl.default}" />'

    @classmethod
    def parse_val(cls, val: Any):
        return val

    @property
    def typ_real(self):
        return self.typ

class PastDateTimeTemplateTag(BaseTemplateTag):
    typ: Literal['PastDateTimeTemplate'] = 'PastDateTimeTemplate'
    default: float = 0

    @classmethod
    def parse_val(cls, val: str):
        if val.count(':') == 1:
            # Seconds are not present in datetime-local
            t = get_time(val + ":00Z")
        else:
            t = get_time(val)
        return t.timestamp()


class PastDateTimeTag(BaseTag):
    val: float # unix
    typ: Literal['PastDateTime'] = 'PastDateTime'

    # def render(self, template: PastDateTimeTemplateTag):
    #     t = get_time(self.val)
    #     return f'<time datetime="{t.strftime("%Y-%m-%dT%H:%M:%S%z")}">{t.strftime("%Y %b %d %H:%M")}</time>'

    def render_val(self, *args):
        t = get_time(self.val)
        return f'<time datetime="{t.strftime("%Y-%m-%dT%H:%M:%S%z")}">{t.strftime("%Y %b %d %H:%M")}</time>'

    def render_input(self, tpl: PastDateTimeTemplateTag, oe: 'store.OverlayEngine'):
        t = get_time(self.val or tpl.default)
        return f'''
            <input
              type="datetime-local"
              name="tag_v2_val"
              value="{t.strftime("%Y-%m-%dT%H:%M:%S")}" /> UTC
        '''

    @property
    def datetime(self):
        return datetime.datetime.fromtimestamp(self.val, ZoneInfo("UTC"))

class EnumTemplateTag(BaseTemplateTag):
    has_groups: bool = False
    values: list[tuple]
    typ: Literal['EnumTemplate'] = 'EnumTemplate'
    default: str = ''

    def get_icon(self, value):
        for (_, val, _, icon) in self.values:
            if val == value:
                return icon
        return '?'

    def render_input(self, current_value, oe):
        out = '<select name="tag_v2_val">'
        if self.has_groups:
            for cat, vs in itertools.groupby(self.values, lambda x: x[0]):
                out += f'<optgroup label="{cat}">'
                for x in vs:
                    (_, value, _, icon) = x
                    selected = ' selected ' if value == current_value else ''
                    out += f'<option value="{value}" {selected}>{icon} {value}</option>'
                out += f'</optgroup>'
        else:
            for x in self.values:
                (_, value, _, icon) = x
                selected = ' selected ' if value == current_value else ''
                out += f'<option value="{value}" {selected}>{icon} {value}</option>'

        return out + '</select>'

class EnumTag(BaseTag):
    val: str
    typ: Literal['Enum'] = 'Enum'

    def render_val(self, template: EnumTemplateTag):
        if template:
            return (template.get_icon(self.val) + " " + self.val).strip()
        else:
            return self.val


class StatusTemplateTag(EnumTemplateTag):
    key: str = 'status'
    title: str = 'Status'
    typ: Literal['StatusTemplate'] = 'StatusTemplate'
    default: str = 'Backlog'
    # TODO: would be better to exclude this from load/restore.
    has_groups: bool = True

    values: list[tuple] = [
        # Category, Value, Color, Icon
        ('To-do', 'Backlog', 'Gray', "🚧"),
        #
        ('In progress', 'Planning', 'Blue', "🚧"),
        ('In progress', 'In-Progress', 'Yellow', "▶️"),
        ('In progress', 'Paused', 'Purple', "⏸️"),
        #
        ('Done', 'Done', 'Green', "✅"),
        ('Done', 'Cancelled', 'Red', '❌')
    ]

class StatusTag(EnumTag):
    typ: Literal['Status'] = 'Status'

class PriorityTemplateTag(EnumTemplateTag):
    key: str = 'priority'
    title: str = 'Priority'
    typ: Literal['PriorityTemplate'] = 'PriorityTemplate'
    default: str = 'Medium'
    has_groups: bool = False

    values: list[tuple] = [
        # Category, Value, Color, Icon
        ('', 'Low', 'Yellow', ''),
        ('', 'Medium', 'Orange', ''),
        ('', 'High', 'Red', ''),
    ]

class PriorityTag(EnumTag):
    typ: Literal['Priority'] = 'Priority'


class TRLTemplateTag(EnumTemplateTag):
    key: str = 'trl'
    title: str = 'Readiness'
    typ: Literal['TRLTemplate'] = 'TRLTemplate'
    default: str = 'TRL-1'
    has_groups: bool = True

    values: list[tuple] = [
        # Category, Value, Color, Icon
        ("Initial", "TRL-0 Not Started", "Gray", "❔"),
        ("Initial", "TRL-1 Basic principles observed", "Gray", "🚧"),
        ("Initial", "TRL-2 Technology concept formulated", "Gray", "🚧"),
        ("Initial", "TRL-3 Experimental proof of concept ", "Gray", "🚧"),
        ("Validation", "TRL-4 Technology validated in lab", "Yellow", "🏗"),
        ("Validation", "TRL-5 Technology validated in relevant environment", "Yellow", "🏗"),
        ("Validation", "TRL-6 Technology demonstrated in relevant environment", "Yellow", "🏗"),
        ("Production", "TRL-7 System prototype demonstration in operational environment", "Yellow", "▶️"),
        ("Production", "TRL-8 System complete and qualified", "Yellow", "▶️"),
        ("Production", "TRL-9 Actual system proven in operational environment", "Yellow", "▶️"),
        ("Done", "TRL-X Cancelled", "Red", "❌")
    ]

class TRLTag(EnumTag):
    val: str
    typ: Literal['TRL'] = 'TRL'


class IconTemplateTag(EnumTemplateTag):
    key: str = 'icon'
    title: str = 'Icon'
    typ: Literal['IconTemplate'] = 'IconTemplate'
    default: str = 'ph-article'
    has_groups: bool = True

    values: list[tuple] = [
        # Category, Value, Color, Icon
        ("Initial", "TRL-0 Not Started", "Gray", "❔"),
        ("Initial", "TRL-1 Basic principles observed", "Gray", "🚧"),
    ]

class IconTag(EnumTag):
    val: str
    typ: Literal['Icon'] = 'Icon'

    def render_input(self, current_value, oe):
        return f"""
<!-- Button trigger modal -->
<input type="hidden" name="tag_v2_val" id="icon-value" value="{self.val}">
<span id="icon-value-visible">
    <i style="font-size:200%" class="ph {self.val}"></i>
</span>
<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#iconSelection">
  Icon Select
</button>
"""
        out = '<select name="asdf">'
        for cat, vs in itertools.groupby(self.values, lambda x: x[0]):
            out += f'<optgroup label="{cat}">'
            for x in vs:
                (_, value, _, icon) = x
                selected = ' selected ' if value == current_value else ''
                out += f'<option value="{value}" {selected}>{icon} {value}</option>'
            out += f'</optgroup>'
        return out + '</select>'


class TextTemplateTag(BaseTemplateTag):
    typ: Literal['TextTemplate'] = 'TextTemplate'
    default: str = ''


class TextTag(BaseTag):
    val: str
    typ: Literal['Text'] = 'Text'

class URLTemplateTag(BaseTemplateTag):
    typ: Literal['URLTemplate'] = 'URLTemplate'
    default: str = ''


class URLTag(BaseTag):
    val: str
    typ: Literal['URL'] = 'URL'

    def render_val(self, *args, **kwargs):
        return f'<a href="{self.val}">{self.val}</a>'


class ReferenceTemplateTag(BaseTemplateTag):
    typ: Literal['ReferenceTemplate'] = 'ReferenceTemplate'
    default: str = ''
    filter: str = 'select urn from __all__ group by type'
    # min? max?

class ReferenceTag(BaseTag):
    val: str # UniformReference.urn
    typ: Literal['Reference'] = 'Reference'


    def render_input(self, template: ReferenceTemplateTag, oe: 'store.OverlayEngine'):
        if template and template.filter:
            urns = oe.query(template.filter)
        else:
            urns = oe.query('group select urn, title, type from __all__ group by type')

        out = '<select name="tag_v2_val" multiple>'
        for group in urns.groups:
            out += f'<optgroup label="{group.title}">'
            for row in group.rows:
                urn = row[0]
                # selected = ' selected ' if value == current_value else ''
                selected = ''
                out += f'<option value="{urn}" {selected}>\n{row[1]}\n</option>\n'
            out += f'</optgroup>'

        return out + '</select>'


class HashtagsTemplateTag(BaseTemplateTag):
    typ: Literal['HashtagsTemplate'] = 'HashtagsTemplate'
    default: list[str] = Field(default_factory=list)
    # min? max?

    @classmethod
    def parse_val(cls, val: Any):
        """For 'complex' types that have different UI presentations, bring them back into our space"""
        return [x.strip() for x in val.split() if x.strip() != '']
        # return ['#' + x.strip() for x in val.split('#') if x.strip() != '']


class HashtagsTag(BaseTag):
    val: list[str]
    typ: Literal['Hashtags'] = 'Hashtags'


    def render_input(self, tpl: BaseTemplateTag, oe: 'store.OverlayEngine'):
        # TODO: escape
        return f'<input type="text" name="tag_v2_val" value="{" ".join(self.val or tpl.default)}" />'

    def render_val(self, template: HashtagsTemplateTag):
        return ' '.join([
            f'''
                <span class="tag" style="background: {hashed_colour(v[1:])}">
                {v}
                </span>
            '''
            for v in self.val
        ])


TagV2 = Annotated[
    PastDateTimeTag | EnumTag | StatusTag | PriorityTag | TextTag |
    ReferenceTag | HashtagsTag | TRLTag | URLTag | IconTag,
    Field(discriminator="typ")
]


TemplateTagV2 = Annotated[
    PastDateTimeTemplateTag | EnumTemplateTag | StatusTemplateTag |
    PriorityTemplateTag | TextTemplateTag | ReferenceTemplateTag |
    HashtagsTemplateTag | TRLTemplateTag | URLTemplateTag | IconTemplateTag,
    Field(discriminator="typ")
]

def realise_tag(t: TemplateTagV2) -> TagV2:
    # Just in case...
    # if 'Template' not in t.__class__.__name__:
    #     return t

    cm = globals()[t.__class__.__name__.replace('Template', '')]
    # print(cm, t, t.instantiate_data())
    return cm.model_validate(t.instantiate_data())




class TemplateValue(BaseModel):
    type: (Literal['enum'] | Literal['status'] | Literal['float'] |
           Literal['urn'] | Literal['date'] | Literal['bool'] | Literal['sql']
           | Literal['str'] | Literal['iso3166'] | Literal['int'] | Literal['future_date'] | Literal['unix_time'] | Literal['rollup'] | Literal['tags'])
    values: Optional[list[str]] = Field(default_factory=list)
    title: Optional[str] = None
    colors: Optional[list[str] | str] = None
    default: Optional[Any] = None
    n_max: int = 1
    n_min: int = 1

    def get_title(self):
        if self.title is None:
            return self.type.title()

    def get_values(self):
        if self.type == 'iso3166':
            return ['DE', 'NL', 'BE', "FR", 'UK']
        else:
            return self.values

    def is_multi(self):
        return self.n_max > 1

    def is_required(self):
        return self.n_min > 0

    def get_val_default(self) -> str:
        if self.default is not None:
            if self.is_multi():
                return FIELD_SEP.join(map(str, self.default))
            else:
                return self.default
        return ''

    def get_tag_value(self, value):
        if self.type == 'unix_time':
            if value:
                get_time(value)
        elif self.type == 'future_date':
            return datetime.datetime.strptime(value, "%Y-%m-%d")
        return value

    # purposely shadow .value on a real tag.
    def value(self):
        return self.val


class Tag(BaseModel):
    # TODO: is there any sane usecase for multi-valued tags that are used everywhere?
    key: str
    val: str | float | bool | int | UniformReference | datetime.datetime

    model_config = ConfigDict(use_enum_values=True)

    @property
    def val_safe(self):
        return self.val

    def value(self, template=None):
        if template:
            return template.get_tag_value(self.key, self.val)
        return self.val

    def render_key(self, template=None):
        if template:
            relevant_template_tag = [x for x in template.thing.data.tags if x.key == self.key]
            if len(relevant_template_tag) > 0:
                relevant_template_tag = relevant_template_tag[0]
                return relevant_template_tag.val.title or relevant_template_tag.key
        return self.key

    def render(self, template, standalone=False):
        if template:
            # TODO: this needs knowledge of the template for e.g. colors
            relevant_template_tag = [x for x in template.thing.data.tags if x.key == self.key]
            if len(relevant_template_tag) > 0:
                relevant_template_tag = relevant_template_tag[0]
                return relevant_template_tag.render_rev(self.val, standalone=standalone)

        if hasattr(self.val, 'html_icon'):
            icon = getattr(self.val, 'html_icon', '!!')
        else:
            icon = ''

        if standalone:
            return f'<span class="tag">{icon} {self.key}={ellips(self.val)}</span>'
        else:
            return f'<span class="tag" title="{self.key}">{icon} {ellips(self.val)}</span>'

    def render_input(self, template):
        if template is None:
            return f"""<input type="text" name="tag_val" placeholder="value" value="{self.val}"/>"""
        # TODO: this needs knowledge of the template.
        relevant_template_tag = [x for x in template.thing.data.tags if x.key == self.key]
        if len(relevant_template_tag) > 0:
            relevant_template_tag = relevant_template_tag[0]
            return relevant_template_tag.render_input_rev(self.val)

        return f"""<input type="text" name="tag_val" placeholder="value" value="{self.val}"/>"""


# Here's notions: https://www.notion.com/help/database-properties
#
# __      Created by       Automatically records the person who created the item. Auto-generated and not editable.
# __      Created time     Records the timestamp of an item's creation. Auto-generated and not editable.
# __      Last edited by   Records the person who edited the item last. Auto-updated and not editable.
# __      Last edited time Records the timestamp of an item's last edit. Auto-updated and not editable.
# bool    Checkbox         Use a checkbox to indicate whether a condition is true or false. Useful for lightweight task tracking.
# date    Date             Accepts a date or a date range (time optional). Useful for deadlines, especially with calendar and timeline views.
# enum    Multi-Select     Choose one or more options from a list of tags. Useful for tagging items across multiple categories.
# enum    Select           Choose one option from a list of tags. Useful for categorization.
# enum(v) Status           Track this item’s progress using status tags categorized by To-do, In Progress, or Complete.
# float   Number           Accepts numbers. These can also be formatted as currency or progress bars. Useful for tracking counts, prices, or completion.
# ref     File             Upload files and images for easy retrieval. Useful for storing documents and photos.
# ref     Person           Tag anyone in your Notion workspace. Useful for assigning tasks or referencing relevant team members.
# ref     Relation         Connect databases and mention database pages. Useful for connecting items across your workspace. Learn more here →
# sql     Formula          Perform calculations based on other properties using Notion’s formula language. Learn more here and here →
# sql     Rollup           View and aggregate information about properties from relation properties. Useful for summarizing interconnected data. Learn more here →
# str     Email            Accepts an email address and launches your mail client when clicked.
# str     Phone            Accepts a phone number and prompts your device to call it when clicked.
# str     Text             Add text that can be formatted. Great for summaries, notes, and descriptions!
# str     URL              Accepts a link to a website and opens the link in a new tab when clicked.
# Not sure about these:
# ??      Button           Automate specific actions with one click. Learn more here →
# ??      ID               Automatically creates a numerical ID for each item. IDs are unique and cannot be manually changed.

class TemplateTag(BaseModel):
    key: str
    val: TemplateValue

    @property
    def val_safe(self):
        return json.dumps(self.val.model_dump())

    def instantiate(self) -> Tag:
        # Turn a TemplateTag into a TagTag

        val = self.val.get_val_default()
        t = Tag(key=self.key, val=val)
        return t

    def render(self, _template=None, standalone=False):
        if standalone:
            return f'<span class="template tag">{self.key}:{ellips(self.val)}</span>'
        return f'<span class="template tag">{ellips(self.val)}</span>'

    # purposely shadow .value on a real tag.
    def value(self, template=None):
        return self.val

    def render_key(self, template=None):
        return self.key

    def render_input(self, value):
        return f"""<input type="text" name="tag_val" placeholder="value" value="{self.val_safe}"/>"""

    def tag_color(self, val):
        if self.val.colors == 'hashed_value':
            m = hashlib.sha256()
            m.update(val.encode('utf-8'))
            m.digest()
            d = int.from_bytes(m.digest()[0:2]) % 360
            x = int.from_bytes(m.digest()[3:5]) % 30
            return f'hsl({d}deg 75% {65 + x}%) !important'
        elif isinstance(self.val.colors, list):
            return self.val.colors[self.val.values.index(val)] + ' !important'

        return 'transparent'

    def render_rev(self, value, standalone=False):
        y = ''
        if standalone:
            y = self.key + '='

        color = self.tag_color(value)

        if self.val.type == 'tags':
            res = ''
            for x in value.split(' '):
                c = self.tag_color(x)
                res += f'<span class="tag" style="background: {c}">{x}</span>'
            return res
        elif self.val.type == 'future_date':
            return f'<span class="tag">{y}{get_time(value).strftime("%Y %b %d")}</span>'
        elif self.val.type == 'unix_time':
            try:
                t = get_time(value)
                return f'<span class="tag">{y}<time datetime="{t.strftime("%Y-%m-%dT%H:%M:%S%z")}">{t.strftime("%Y %b %d %H:%M")}</time></span>'
            except:
                return f'<span class="tag">{y}{value}</span>'

        elif self.val.type == 'status':
            icon = {
                'done': "✅",
                'inprogress': "🚧",
                'planning': "🚧",
                'backlog': "🚧",
                'blocked': "🚫",
                'canceled': "❌",
                'cancelled': "❌"
            }
            zicon = icon.get(value, "📝")
            if standalone:
                return f'<span class="tag">{y}{value}</span>'
            else:
                return f'<span class="tag">{zicon} {value}</span>'

        return f'<span class="tag">‽ {value}</span>'

    def render_input_rev(self, value):
        if self.val.type in ('status', 'enum', 'iso3166') :
            out = """<select name="tag_val">"""
            for option in (self.val.values or []):
                if option == value:
                    out += f'<option value="{option}" selected>{option}</option>'
                else:
                    out += f'<option value="{option}">{option}</option>'
            return out + '</select>'
        return f"""<input type="text" name="tag_val" placeholder="value" value="{value}"/>"""
