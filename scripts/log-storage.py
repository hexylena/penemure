from penemure.logs import *


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



t = TimeTravelDict.reconstruct_from_file()
print(t.data)

print('------')
q = safe(t.data)
print(q)
u = unsafe(q)
print(u)

print('=======')





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
