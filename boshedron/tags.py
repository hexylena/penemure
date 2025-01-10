from pydantic import BaseModel, Field, AwareDatetime
from typing import Optional, Union
from enum import Enum
from .refs import *


class LifecycleEnum(str, Enum):
    backlog = 'backlog'
    planning = 'planning'
    inprogress = 'in-progress'
    blocked = 'blocked'
    paused = 'paused'
    done = 'done'
    canceled = 'canceled'

    def icon(self):
        if self == LifecycleEnum.done:
            return "✅"
        elif self == LifecycleEnum.inprogress or self == LifecycleEnum.planning:
            return "🚧"
        elif self == LifecycleEnum.blocked:
            return "🚫"
        else:
            return "📝"


class Tag(BaseModel):
    # TODO: is there any sane usecase for multi-valued tags that are used everywhere?
    type: str = 'tag'
    title: str = 'Tag'
    icon: Optional[Union[str, Reference, BlobReference, ExternalReference]] = None

    @property
    def key(self) -> str:
        return self.type

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

class LifecycleTag(Tag):
    type: str = 'status'
    title: str = 'Status'
    value: LifecycleEnum = LifecycleEnum.backlog

    @property
    def html_icon(self):
        return "🚦"

    def render(self):
        return str(self.value.value)

class DateTag(Tag):
    type: str = 'date'
    title: str = 'Date'
    value: AwareDatetime
    period: str = 'start'

    @property
    def html_icon(self):
        return "📅"

    def render(self):
        return self.value

class AccountTag(Tag):
    type: str = 'reference'
    values: list[UniformReference] = Field(default_factory=list)

    @property
    def html_icon(self):
        return "👤"

    def render(self):
        return ', '.join([x.urn for x in self.values])

class TextTag(Tag):
    value: str = ''

    @property
    def html_icon(self) -> str:
        return "📝"

    def render(self):
        return self.value


class DescriptionTag(TextTag):
    type: str = 'description'
    value: str = ''


class IconTag(TextTag):
    type: str = 'icon'
