import hashlib
import jsondiff
import base64
import json
import copy
from pydantic import BaseModel, Field
from typing import Annotated, Any, Literal


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

LogEntry = Annotated[
    SetLog | DelLog,
    Field(discriminator="action")
]

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
def emit(after: dict, before: dict = {}) -> list[LogEntry]:
    # Our life is easier if modifications are not made at the top level.
    b_s = safe(before)
    a_s = safe(after)
    res = []
    for k, v in jsondiff.diff(b_s, a_s).items():
        for x in rec({k: v}):
            res.append(x)

    # Ordering is important here, `__order` changes should come last.
    res = sorted(res, key=lambda path: '__order' in path[0])
    return res
