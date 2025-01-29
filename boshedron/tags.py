from pydantic import BaseModel, Field, NaiveDatetime
import json
from typing import Literal
from pydantic import ConfigDict
from typing import Optional, Union, Any
from enum import Enum
import datetime
from zoneinfo import ZoneInfo
from .refs import *

FIELD_SEP = chr(0x001E)


class LifecycleEnum(Enum):
    backlog = 'backlog'
    planning = 'planning'
    inprogress = 'in-progress'
    blocked = 'blocked'
    paused = 'paused'
    done = 'done'
    canceled = 'canceled'

    @property
    def html_icon(self):
        if self == LifecycleEnum.done:
            return "✅"
        elif self == LifecycleEnum.inprogress or self == LifecycleEnum.planning:
            return "🚧"
        elif self == LifecycleEnum.blocked:
            return "🚫"
        else:
            return "📝"


class TemplateValue(BaseModel):
    type: (Literal['enum'] | Literal['status'] | Literal['float'] |
           Literal['urn'] | Literal['date'] | Literal['bool'] | Literal['sql']
           | Literal['str'] | Literal['iso3166'] | Literal['int'] | Literal['future_date'] | Literal['unix_time'])
    values: Optional[list[str]] = Field(default_factory=list)
    title: Optional[str] = None
    colors: Optional[list[str]] = None
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

    def render(self):
        if hasattr(self.val, 'html_icon'):
            return getattr(self.val, 'html_icon', '!!') + " " + str(self.val)
        # TODO: this needs knowledge of the template for e.g. colors
        return f'<span class="tag" title="{self.key}">{self.icon} {self.val}</span>'

    def val_input(self):
        # TODO: this needs knowledge of the template.
        pass

    @property
    def icon(self) -> str:
        if self.key == 'status':
            if self.val == 'done':
                return "✅"
            elif self.val in ('inprogress', 'planning', 'backlog'):
                return "🚧"
            elif self.val == 'blocked':
                return "🚫"
            else:
                return "📝"

        return '‽'


#
#     @property
#     def html_icon(self) -> str:
#         if self.title == "Status":
#             return "🚦"
#         elif self.title == "Assignee" or self.title == "assignee":
#             return "👤"
#         elif self.title == "Author":
#             return "👤"
#         elif self.title == "Tags":
#             return "🏷"
#         elif self.title == "Due":
#             return "📅"
#         elif self.title == "Estimate":
#             return "⏱"
#         elif self.type == "time":
#             return "⏱"
#         elif self.title == "Priority":
#             return "🔥"
#         elif self.title == "Effort":
#             return "🏋️"
#         elif self.title == "Progress":
#             return "📈"
#         elif self.title == "Start":
#             return "🏁"
#         elif self.title == "End":
#             return "🏁"
#         elif self.title == "Created":
#             return "📅"
#         elif self.title == "Modified":
#             return "📅"
#         elif self.title == "Completed":
#             return "📅"
#         elif self.title == "Blocked":
#             return "🚫"
#         elif self.title == "Blocking":
#             return "🚫"
#
#         return ""
#
#     # https://github.com/pydantic/pydantic/discussions/3091
#     # @staticmethod
#     # def from_dict(obj: dict[str, Any]):
#     #     m = {x.model_fields['type'].default: x for x in Tag.get_subclasses()}
#     #     if 'type' not in obj:
#     #         raise ValueError("Missing type attribute of object")
#     #
#     #     if obj['type'] not in m:
#     #         raise ValueError("Unknown model")
#     #
#     #     return m[obj['type']].model_validate(obj)
#     #
#     # https://github.com/pydantic/pydantic/discussions/3091
#     @classmethod
#     def get_subclasses(cls):
#         return tuple(cls.__subclasses__())
#     #
#     # # https://github.com/pydantic/pydantic/discussions/3091
#     # @classmethod
#     # def model_validate(cls, obj, *args, **kwargs):
#     #     if cls.__name__ == "Tag":
#     #       return Tag.from_dict(obj, *args, **kwargs)
#     #     return super().model_validate(obj, *args, **kwargs)
#
#
# # class LifecycleTag(Tag):
# #     type: Literal['status'] = 'status'
# #     title: str = 'Status'
# #     value: LifecycleEnum
# #
# #     @property
# #     def html_icon(self):
# #         return "🚦"
# #
# #     def value_icon(self):
# #         if self.value == 'done':
# #             return "✅"
# #         elif self.value == 'in-progress' or self == 'planning':
# #             return "🏃‍♀️"
# #         elif self.value == 'blocked':
# #             return "🚧"
# #         elif self.value == 'canceled':
# #             return "🚫"
# #         else:
# #             return "📝"
# #
# #     def render(self):
# #         if self.value_icon() is not None:
# #             return f'<span class="tag">{self.value_icon()} {self.value}</span>'
# #         return str(self.value)
# #
# # class DateTimeTag(Tag):
# #     type: Literal['date'] = 'date'
# #     title: str = 'Date'
# #     timezone: str = 'Europe/Amsterdam'
# #     value: NaiveDatetime = Field(default_factory=lambda: datetime.now())
# #
# #     @property
# #     def datetime(self):
# #         return self.value.astimezone(ZoneInfo(self.timezone))
# #
# #     def render(self):
# #         return f'<span class="tag">{self.type}:{self.value} {self.timezone}</span>'
# #
# #     @property
# #     def html_icon(self):
# #         return "📅"
# #
# # class ReferenceTag(Tag):
# #     type: Literal['reference'] = 'reference'
# #     value: UniformReference
# #     title: str = 'Reference'
# #
# #     @property
# #     def html_icon(self):
# #         return "👤"
# #
# #     def render(self):
# #         return self.value.urn
# #
# # class IdTag(Tag):
# #     type: Literal['id'] = 'id'
# #     value: int
# #     group: str
# #     title: str = '№'
# #
# #     def render(self):
# #         return f"{self.group}-{self.value}"
# #
# #
# # class NumericTag(Tag):
# #     type: Literal['numeric'] = 'numeric'
# #     value: float
# #     fmt: str = '{:0.2f}'
# #     title: str = 'Number'
# #
# #     def render(self):
# #         return self.fmt.format(self.value)
# #
# # class TextTag(Tag):
# #     type: Literal['text'] = 'text'
# #     value: str = ''
# #     title: str = 'Text'
# #
# #     @property
# #     def html_icon(self) -> str:
# #         return "📝"
# #
# # class DescriptionTag(Tag):
# #     type: Literal['description'] = 'description'
# #     value: str = ''
# #     title: str = 'Description'
# #
# #
# # class IconTag(Tag):
# #     type: Literal['icon'] = 'icon'
# #     title: str = 'Icon'
# #     value: str = ''
# #
# #     @property
# #     def html_icon(self) -> str:
# #         return str(self.value)
# #
# #     # def render(self):
# #     #     return f'<span class="icon">{self.value_icon()}</span>'
# #
# #
# # class TemplateTag(Tag):
# #     type: Literal['template'] = 'template'
# #     value: str = 'note.html'
# #     title: str = 'Template'

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

    def render(self):
        if hasattr(self.val, 'html_icon'):
            return getattr(self.val, 'html_icon', '!!') + " " + str(self.val)
        return f'<span class="template tag">{self.val}</span>'

    # purposely shadow .value on a real tag.
    def value(self, template=None):
        return self.val
