from pydantic import BaseModel, Field, PrivateAttr
import time

###
# Idea: can a dict track itself such that any modifications are emitted as some useful annotation for our LSM
#
# Conclusions:
# - No it is hard to capture everything
# - It's going to be bloody annoying to apply atop pydantic
# - It'll be easier to diff two dicts.



class TrackedList(list):
    _logs: list
    _path: list[str]

    def __init__(self, d: list=None, path:list[str] = None):
        for x in d:
            self.append(x)

        self._path = path if path else []
        self._logs = []

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            td = TrackedDict(d=value, path=self._path + [key])
        elif isinstance(value, list):
            td = TrackedList(d=value, path=self._path + [key])
        else:
            td = value
        super(TrackedList, self).__setitem__(key, td)

        self._logs.append({
            "ts": time.time(),
            "k": self._path + [key],
            "a": "set",
            "v": value
        })

    def append(self, value):
        if isinstance(value, dict):
            td = TrackedDict(d=value, path=self._path + [len(self)])
        elif isinstance(value, list):
            td = TrackedList(d=value, path=self._path + [len(self)])
        else:
            td = value
        super(TrackedList, self).append(value)

        if not hasattr(self, '_logs'):
            self._logs = []
        self._logs.append({
            "ts": time.time(),
            "k": self._path + [len(self) - 1],
            "a": "set",
            "v": value
        })

    def _emit(self):
        logs = []

        for v in self:
            if isinstance(v, TrackedDict) or isinstance(v, TrackedList):
                logs.extend(v._emit())
            else:
                pass
        logs.extend(self._logs)
        return sorted(logs, key=lambda x:x['ts'])


class TrackedDict(dict):
    _logs: list
    _path: list[str]

    def __init__(self, d: dict=None, path:list[str] = None):
        if d:
            for k, v in d.items():
                self[k] = v

        if path:
            self._path = path
        else:
            self._path = list()
        self._logs = []


    def __setitem__(self, key, value):
        if isinstance(value, dict):
            td = TrackedDict(d=value, path=self._path + [key])
        elif isinstance(value, list):
            td = TrackedList(d=value, path=self._path + [key])
        else:
            td = value
        super(TrackedDict, self).__setitem__(key, td)

        self._logs.append({
            "ts": time.time(),
            "k": self._path + [key],
            "a": "set",
            "v": value
        })

    def _emit(self):
        logs = []
        for _, v in self.items():
            if isinstance(v, TrackedDict) or isinstance(v, TrackedList):
                logs.extend(v._emit())
            else:
                pass
        logs.extend(self._logs)
        return sorted(logs, key=lambda x:x['ts'])

    # def _debug(self, indent=0):
    #     for k, v in self.items():
    #         if isinstance(v, dict):
    #             self._debug(indent=2)
    #         else:
    #             print(f'{" " * indent}k={k} type={type(v)} v={v}')




t = TrackedDict()
t['key'] = "val"
t['a'] = {}
t['a']['b'] = 'val'
t['b'] = {}
t['b']['c'] = 1
t['b']['c'] += 1
t['l1'] = []
print(t)
t['l2'] = [1]
t['l'] = [1,2,3]
t['l'].append(1)

for log in t._emit():
    print(log)
