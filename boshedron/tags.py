from pydantic import BaseModel, Field, NaiveDatetime
from typing import Literal
from pydantic import ConfigDict
from typing import Optional, Union, Any
from enum import Enum
from datetime import datetime
from zoneinfo import ZoneInfo
from .refs import *


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


##
# Theory: all tags are k:v where v is singular. if you want multiple V, add
# multiple tags.
#
# (this... sucks? but the data modelling is easier.)

class Tag(BaseModel):
    # TODO: is there any sane usecase for multi-valued tags that are used everywhere?
    type: Any
    title: str = 'Tag' # Displayed for user?
    icon: Optional[Union[str, Reference, BlobReference, ExternalReference]] = None
    value: Optional[Any]

    model_config = ConfigDict(use_enum_values=True)

    @property
    def key(self) -> str:
        return getattr(self, 'type', 'tag')

    def render(self):
        if hasattr(self.value, 'html_icon'):
            return getattr(self.value, 'html_icon', '!!') + " " + str(self.value)
        return f'<span class="tag">{self.type}:{self.value}</span>'

    @property
    def html_icon(self) -> str:
        if self.title == "Status":
            return "🚦"
        elif self.title == "Assignee" or self.title == "assignee":
            return "👤"
        elif self.title == "Author":
            return "👤"
        elif self.title == "Tags":
            return "🏷"
        elif self.title == "Due":
            return "📅"
        elif self.title == "Estimate":
            return "⏱"
        elif self.type == "time":
            return "⏱"
        elif self.title == "Priority":
            return "🔥"
        elif self.title == "Effort":
            return "🏋️"
        elif self.title == "Progress":
            return "📈"
        elif self.title == "Start":
            return "🏁"
        elif self.title == "End":
            return "🏁"
        elif self.title == "Created":
            return "📅"
        elif self.title == "Modified":
            return "📅"
        elif self.title == "Completed":
            return "📅"
        elif self.title == "Blocked":
            return "🚫"
        elif self.title == "Blocking":
            return "🚫"

        return ""

    # https://github.com/pydantic/pydantic/discussions/3091
    # @staticmethod
    # def from_dict(obj: dict[str, Any]):
    #     m = {x.model_fields['type'].default: x for x in Tag.get_subclasses()}
    #     if 'type' not in obj:
    #         raise ValueError("Missing type attribute of object")
    #
    #     if obj['type'] not in m:
    #         raise ValueError("Unknown model")
    #
    #     return m[obj['type']].model_validate(obj)
    #
    # https://github.com/pydantic/pydantic/discussions/3091
    @classmethod
    def get_subclasses(cls):
        return tuple(cls.__subclasses__())
    #
    # # https://github.com/pydantic/pydantic/discussions/3091
    # @classmethod
    # def model_validate(cls, obj, *args, **kwargs):
    #     if cls.__name__ == "Tag":
    #       return Tag.from_dict(obj, *args, **kwargs)
    #     return super().model_validate(obj, *args, **kwargs)


class LifecycleTag(Tag):
    type: Literal['status'] = 'status'
    title: str = 'Status'
    value: LifecycleEnum

    @property
    def html_icon(self):
        return "🚦"

    def value_icon(self):
        if self.value == 'done':
            return "✅"
        elif self.value == 'in-progress' or self == 'planning':
            return "🏃‍♀️"
        elif self.value == 'blocked':
            return "🚧"
        elif self.value == 'canceled':
            return "🚫"
        else:
            return "📝"

    def render(self):
        if self.value_icon() is not None:
            return f'<span class="tag">{self.value_icon()} {self.value}</span>'
        return str(self.value)

class DateTimeTag(Tag):
    type: Literal['date'] = 'date'
    title: str = 'Date'
    timezone: str = 'Europe/Amsterdam'
    value: NaiveDatetime = Field(default_factory=lambda: datetime.now())

    @property
    def datetime(self):
        return self.value.astimezone(ZoneInfo(self.timezone))

    def render(self):
        return f'<span class="tag">{self.type}:{self.value} {self.timezone}</span>'

    @property
    def html_icon(self):
        return "📅"

class ReferenceTag(Tag):
    type: Literal['reference'] = 'reference'
    value: UniformReference
    title: str = 'Reference'

    @property
    def html_icon(self):
        return "👤"

    def render(self):
        return self.value.urn

class IdTag(Tag):
    type: Literal['id'] = 'id'
    value: int
    group: str
    title: str = '№'

    def render(self):
        return f"{self.group}-{self.value}"


class NumericTag(Tag):
    type: Literal['numeric'] = 'numeric'
    value: float
    fmt: str = '{:0.2f}'
    title: str = 'Number'

    def render(self):
        return self.fmt.format(self.value)

class TextTag(Tag):
    type: Literal['text'] = 'text'
    value: str = ''
    title: str = 'Text'

    @property
    def html_icon(self) -> str:
        return "📝"

class DescriptionTag(Tag):
    type: Literal['description'] = 'description'
    value: str = ''
    title: str = 'Description'


class IconTag(Tag):
    type: Literal['icon'] = 'icon'
    title: str = 'Icon'
    value: str = ''

    @property
    def html_icon(self) -> str:
        return str(self.value)

    # def render(self):
    #     return f'<span class="icon">{self.value_icon()}</span>'


class TemplateTag(Tag):
    type: Literal['template'] = 'template'
    value: str = 'note.html'
    title: str = 'Template'
