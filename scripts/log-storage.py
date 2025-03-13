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
# 1  | key | set | val    | {"key": "val"}
# 2  | a.b | set | val    | {"key": "val", "a": {"b": "val"}}
# 3  | l   | ins | [0]    | {"key": "val", "a": {"b": "val"}, "l": []}
# 4  | l   | ins | [0, 1] | {"key": "val", "a": {"b": "val"}, "l": [1]}
# 5  | l   | ins | [0, 2] | {"key": "val", "a": {"b": "val"}, "l": [2,1]}
# 6  | l   | ins | [1, 3] | {"key": "val", "a": {"b": "val"}, "l": [2,3,1]}
# 7  | l   | del | 1      | {"key": "val", "a": {"b": "val"}, "l": [2,1]}
# 8  | l   | set | [0]    | {"key": "val", "a": {"b": "val"}, "l": [0]}
# 9  | key | del | None   | {"a": {"b": "val"}, "l": [0]}
# 10 | a   | new | {}     | {"key": "val", "a": {"b": "val"}, "l": [0], "a": {}}

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


class BaseLog(BaseModel):
    timestamp: int | float = Field(alias="ts")
    actor: str             = Field(alias="u")
    key: list[Any]         = Field(alias="k") # probably it's Hashable, not sure that's a type?

class SetLog(BaseLog):
    action: Literal['set'] = Field(alias="a", default='set')
    value: Any             = Field(alias="v")

    def apply(self, d: dict) -> dict:
        # print(f'apply, d={d}')
        value = d
        for key in self.key[0:-1]:
            if isinstance(value, dict):
                if key not in value:
                    value[key] = {}
                value = value[key]
                continue

        if isinstance(value, dict):
            value[self.key[-1]] = self.value
        else:
            raise KeyError(f"Could not set {value} to {self.value}")
        # print(f'       d={d}')
        return d


# DEPRECATE
class InsLog(BaseModel):
    timestamp: int | float = Field(alias="ts")
    key: list[str | int]   = Field(alias="k")
    action: Literal['ins'] = Field(alias="a")
    value: tuple[int, Any] = Field(alias="v")

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.key[:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        lk = self.key[-1]
        # if isinstance(value, str) or isinstance(value, dict):
        #     raise KeyError(f"Could not set {value}:{lk} to {self.v}")

        position, set_value = self.value
        value[lk] = value[lk][0:position] + [set_value] + value[lk][position:]
        return d

class DelLog(BaseLog):
    action: Literal['del']  = Field(alias = "a", default='del')
    value: int | None      = Field(alias = "v")

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.key[:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        lk = self.key[-1]
        # print(f'apply dellog, {self.key} => {lk}: {d}')
        position = self.value
        # If it's a list, and we have a real position, excise
        if isinstance(value[lk], list) and position is not None:
            # print(f'apply dellog a')
            value[lk] = value[lk][0:position] + value[lk][position + 1:]
        elif isinstance(value[lk], dict) and position is None:
            # print(f'apply dellog b, removing {lk} from {value}')
            value[lk] = None
            del value[lk]
        elif isinstance(value, dict) and position is None:
            # print(f'apply dellog c')
            del value[lk]
        else:
            raise Exception(f"Couldn't handle {value[lk]} and {position}")

        # print(f'apply dellog b = {d}')
        return d

class NewLog(BaseLog):
    action: Literal['new']                   = Field(alias = "a")
    value: Literal['list'] | Literal['dict'] = Field(alias = "v")

    def apply(self, d: dict) -> dict:
        value = d
        for key in self.key[0:-1]:
            if isinstance(value, dict):
                value = value[key]
                continue
            elif isinstance(value, list) and isinstance(key, int):
                value = value[key]

        if self.value == 'list':
            value[self.key[-1]] = []
        elif self.value == 'dict':
            value[self.key[-1]] = {}
        else:
            raise Exception()

        return d

LogEntry = Annotated[
    SetLog | DelLog | NewLog | InsLog,
    Field(discriminator="action")
]

class TimeTravelSafeDict(BaseModel):
    pass

class TimeTravelDict(BaseModel):
    data: dict = Field(default_factory=dict)
    logs: list[LogEntry] = Field(default_factory=list)

    @classmethod
    def reconstruct_from_file(cls, ts=0):
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
            # print(f"{str(d):40s} | {op}")
        m.data = d
        return m

    @classmethod
    def reconstruct(cls, logs, ts=0):
        d = {}
        m = cls.model_validate({"logs": copy.deepcopy(logs)})
        for op in logs:
            if ts > 0 and op.timestamp > ts:
                break
            d = op.apply(d)
            print(f"{op}")
            # print(f"{d}")
        m.data = unsafe(d)
        return m

def safe(data):
    c = copy.deepcopy(data)

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
    return {'root': c}

def unsafe(data):
    c = copy.deepcopy(data)

    def rewrite(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if isinstance(v, dict) and '__order' in v:
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
    return c['root']

t = TimeTravelDict.reconstruct_from_file()
print(t.data)

print('------')
q = safe(t.data)
print(q)
u = unsafe(q)
print(u)

print('=======')


def rec(d, path=None):
    # print(f'rec {path}')
    if path is None:
        path = []

    for k, v in d.items():
        if isinstance(k, jsondiff.symbols.Symbol):
            if k.label == 'replace':
                if path == []:
                    for a, b in v.items():
                        yield ([a], 'set', b)
                else:
                    yield (path, 'set', v)
            elif k.label == 'delete':
                if path == []:
                    for a, b in v.items():
                        yield ([a], 'del', b)
                else:
                    yield (path, 'del', v)
            else:
                print(k, v)
                raise Exception(f'Unsupported action: {k}')
        elif isinstance(v, dict):
            yield from rec(v, path + [k])
        else:
            yield (path + [k], 'set', v)


# I think this is the API we want.
def emit(after: dict, before: dict = None) -> list[LogEntry]:
    if before is None:
        before = {}

    # Our life is easier if modifications are not made at the top level.
    b_s = safe(before)
    a_s = safe(after)
    res = []
    for k, v in jsondiff.diff(b_s, a_s).items():
        # if isinstance(k, jsondiff.symbols.Symbol):
        #     # TODO:
        #     print(type(k), k, v)
        # else:
        for x in rec({k: v}):
            res.append(x)

    # Ordering is important here, `__order` changes should come last.
    res = sorted(res, key=lambda path: '__order' in path[0])
    return res

timeline = [
    {}, # should start empty.
    {'foo': 'bar', 1: 2},
    {'foo': 'bar', 1: 10},
    {'foo': 'bar', 1: 10, 'a': [0]},
    {'foo': 'bar', 1: 10, 'a': [0, 1]},
    {'foo': 'bar', 1: 10, 'a': [0, 1, 3]},
    {'foo': 'bar', 1: 10, 'z': {'b': {'c': 'd'}}},
    # {'foo': 'bar', 1: 10, 'z': {'b': {'c': 'd'}}, 'a': {'b': {'c': 'd'}}},
    # {'foo': 'bar', 1: 10, 'z': {'b': {'c': 'f'}}, 'a': {'b': {'c': 'e'}}},
    # {'foo': 'bar', 1: 10, 'z': {'b': {'c': 'f'}}, 'a': {'b': {'c': None}}},
    # {'foo': 'bar', 1: 10, 'z': {'b': {'c': 'f'}}, 'a': {'b': {}}},
    {},
]

logs = []
for i in range(1, len(timeline)):
    print(f'=> {i}')
    # print(f'   before={timeline[i - 1]}, after={timeline[i]}')
    for log in emit(before=timeline[i - 1], after=timeline[i]):
        (path, action, value) = log
        if action == 'set':
            l = SetLog(ts=i, u='hexy', k=path, v=value)
        else:
            print(path, action, value)
            l = DelLog(ts=i, u='hexy', k=path + value, v=None)

        logs.append(l)
        print('[+]', l.model_dump())

print('reconstruct')
# d = {}
# timeline2 = [copy.copy(d)]
# for log in logs:
#     print('[~]', d)
#     # References are hard ok.
#     # Unsafe was still somehow returning a pointer.
#     print('[~]', repr(log))
#     d = log.apply(d)
#     # print('[?]', d)
#     timeline2.append(unsafe(d))
#     # print('[?]', d)
#     # d = log.apply(d)
for log in logs:
    print('log', log)

# The timelines are different lengths, that is .. expected. As a result of some
# operations being decomposed into *two* operations (e.g. insert item / update
# order)

# log timestamp=1 actor='hexy' key=['root'] action='set' value={'foo': 'bar', 1: 10, 'a': {'z80ghJXV': 0, '__order': 'z80ghJXV'}}
# log timestamp=2 actor='hexy' key=['root', 'a', 'xMpCOKC5'] action='set' value=1
# log timestamp=2 actor='hexy' key=['root', 'a', '__order'] action='set' value='z80ghJXV|xMpCOKC5'
# log timestamp=3 actor='hexy' key=['root', 'a', '7MvIfktc'] action='set' value=3
# log timestamp=3 actor='hexy' key=['root', 'a', '__order'] action='set' value='z80ghJXV|xMpCOKC5|7MvIfktc'
# log timestamp=4 actor='hexy' key=['root', 'z', 'b', 'c'] action='set' value='d'
# log timestamp=4 actor='hexy' key=['root', 'a'] action='del' value=None
# log timestamp=5 actor='hexy' key=['root'] action='set' value={}

# I don't want to implement transactions, that, sounds painful.
# Maybe fine to just compare up to specific timestamps?

print('RECONSTRUCT')
for i in range(len(timeline)):
    print('R', i, timeline[i], TimeTravelDict.reconstruct(logs, ts=i).data)

# for a, b in zip(timeline2, timeline):
#     print(f'a={a}')
#     print(f'b={b}')
#     print()
