from penemure.apps import *
from penemure.main import *
from pydantic_changedetect import ChangeDetectionMixin
from pydantic import BaseModel
from typing import Optional, Annotated


# structures:
# set key, value pair
#
# list creation?
# list insertion
# list removal / tombstone
#
# for everything: timestamp, path, value?
#
# 1   key   set   val      # {"key": "val"}
# 2   a|b   set   val      # {"key": "val", "a": {"b": "val"}}
#
# 3   l     ins    [0]     # {"key": "val", "a": {"b": "val"}, "l": []}
# 4   l     ins    [0, 1]  # {"key": "val", "a": {"b": "val"}, "l": [1]}
# 5   l     ins    [0, 2]  # {"key": "val", "a": {"b": "val"}, "l": [2,1]}
# 6   l     ins    [1, 3]  # {"key": "val", "a": {"b": "val"}, "l": [2,3,1]}
# 7   l     del    1       # {"key": "val", "a": {"b": "val"}, "l": [2,1]}
# 8   l     set    [0]     # {"key": "val", "a": {"b": "val"}, "l": [0]}
#
# 9   key   del    None    # {"a": {"b": "val"}, "l": [0]}
#
# 10  a     new    {}      # {"key": "val", "a": {"b": "val"}, "l": [0], "a": {}}


class SetLog(BaseModel):
    ts: int | float
    k: list[str | int]
    a: Literal['set']
    v: Any

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.k[0:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        if isinstance(self.k[-1], str) and isinstance(value, dict):
            value[self.k[-1]] = self.v
        elif isinstance(self.k[-1], int) and isinstance(value, list):
            value[self.k[-1]] = self.v
        else:
            raise KeyError(f"Could not set {value} to {self.v}")
        return d


class InsLog(BaseModel):
    ts: int | float
    k: list[str | int]
    a: Literal['ins']
    v: tuple[int, Any]

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.k[:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        lk = self.k[-1]
        # if isinstance(value, str) or isinstance(value, dict):
        #     raise KeyError(f"Could not set {value}:{lk} to {self.v}")

        position, set_value = self.v
        value[lk] = value[lk][0:position] + [set_value] + value[lk][position:]
        return d

class DelLog(BaseModel):
    ts: int | float
    k: list[str | int]
    a: Literal['del']
    v: int | None

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.k[:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        lk = self.k[-1]
        position = self.v
        # If it's a list, and we have a real position, excise
        if isinstance(value[lk], list) and position is not None:
            value[lk] = value[lk][0:position] + value[lk][position + 1:]
        elif isinstance(value[lk], dict) and position is None:
            del value[lk]
        elif isinstance(value, dict) and position is None:
            del value[lk]
        else:
            raise Exception(f"Couldn't handle {value[lk]} and {position}")

        return d

class NewLog(BaseModel):
    ts: int | float
    k: list[str | int]
    a: Literal['new']
    v: Literal['list'] | Literal['dict']

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.k[0:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        if self.v == 'list':
            value[self.k[-1]] = []
        elif self.v == 'dict':
            value[self.k[-1]] = {}
        else:
            raise Exception()

        return d

LogEntry = Annotated[
    SetLog | InsLog | DelLog | NewLog,
    Field(discriminator="a")
]


class TimeTravelDict(BaseModel):
    data: dict = Field(default_factory=dict)
    logs: list[LogEntry] = Field(default_factory=list)

    @classmethod
    def reconstruct(cls, ts=0):
        with open('scripts/log.txt', 'r') as handle:
            logs = []
            for line in handle.readlines():
                if line.startswith('#'): continue
                data = json.loads(line.strip())
                if ts > 0:
                    if data['ts'] > ts:
                        break

                logs.append(data)

        m = cls.model_validate({"logs": logs})
        d = {}
        for op in m.logs:
            d = op.apply(d)
            print(f"{str(d):40s} | {op}")
        m.data = d

        return m

t = TimeTravelDict.reconstruct()
print(t)
