from pydantic import BaseModel, Field, NaiveDatetime
import hashlib
import json
from typing import Literal
from pydantic import ConfigDict
from typing import Optional, Union, Any
import datetime
from zoneinfo import ZoneInfo
from .refs import *
from .util import *

FIELD_SEP = chr(0x001E)


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
            return datetime.datetime.fromtimestamp(float(value), ZoneInfo('UTC'))
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
            t = get_time(value)
            return f'<span class="tag">{y}<time datetime="{t.strftime("%Y-%m-%dT%H:%M:%S%z")}">{t.strftime("%Y %b %d %H:%M")}</time></span>'
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
