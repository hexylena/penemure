from penemure.apps import *
import hashlib
import copy
from penemure.main import *
from pydantic_changedetect import ChangeDetectionMixin
from pydantic import BaseModel
from typing import Optional, Annotated


# 2025-03-11
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

# 2025-03-12
# Ideas:
# - diff objects rather than tracking
# - automatically transform lists like [1,2,3] into {"order": "de,ad,be", "de": 1, "ad": 2, "be": 3} which can be more safely manipulated.
#   The hashes could even be from the contents of the value, just, hash the
#   content and we can more safely just re-set every one of them, and remove
#   all that aren't expected.
# See: web+penemure://urn:penemure:d1a8175b-e3f1-4937-8d0c-eab495479c78

a = {"z": "z", "key": "val", "d": {"b": "val"}, "l": [3], "a": {}}
b = {"z": "z", "key": "baz", "c": {"b": "val"}, "l": [0, 3, 1], "a": {}}

# a = {"l": [1,2,3], "a": {}}
# b = {"l": [3,2,1], "a": {}}
# l {insert: [(1, 2), (2, 1)], delete: [1, 0]}
# this looks too complicated to handle safely...

# Neither of these were sufficient
# import recursive_diff
# for x in recursive_diff.recursive_diff(a, b):
#     print(x)
#
# import deep
# diff = deep.diff(a, b)
# if diff:
#     diff.print_full()

# But this is
import jsondiff
for k, v in jsondiff.diff(a, b).items():
    print(k, v)

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


# DEPRECATE
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
    SetLog | DelLog | NewLog | InsLog,
    Field(discriminator="a")
]

class TimeTravelSafeDict(BaseModel):
    pass

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

def safe(data):
    c = copy.copy(data)

    # de-dupe. but duplicated items is extremely, extremely unlikely.
    def kf(i, k, v):
        ib = json.dumps(v, sort_keys=True).encode('utf-8')
        h = hashlib.md5(ib).digest()
        return base64.b64encode(h).decode('utf-8')[0:8]

    # doesn't get us de-duplication.
    # also may generate uglier diffs when we rearrange things
    # def kf(i, k, v):
    #     return str(i)

    def rewrite(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, list):
                    x[k] = {}
                    o = []
                    for i, vv in enumerate(v):
                        hk = kf(i, k, vv)
                        x[k][hk] = vv
                        o.append(hk)
                    x[k]['__order'] = '|'.join(o)
                else:
                    rewrite(v)
        else:
            pass

    rewrite(c)
    return c

def unsafe(data):
    c = copy.copy(data)

    def rewrite(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if '__order' in v:
                    ks = x[k]['__order'].split('|')
                    x[k] = [
                        x[k][zz]
                        for zz in ks
                    ]
                else:
                    rewrite(v)
        else:
            pass

    rewrite(c)
    return c

t = TimeTravelDict.reconstruct()
print(t.data)

print('------')
q = safe(t.data)
print(q)
u = unsafe(q)
print(u)
