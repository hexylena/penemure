from boshedron.store import FsBackend, OverlayEngine, StoredThing
from boshedron.note import Note, MarkdownBlock, UnresolvedReference, LifecycleEnum
from boshedron.apps import *
from boshedron.main import *
from datetime import datetime
from zoneinfo import ZoneInfo

gb1 = FsBackend(name='main', path='projects/main')
gb2 = FsBackend(name='alt', path='./projects/alt')

bos = Boshedron(backends=[gb1, gb2])
oe = bos.overlayengine
oe.load()

# account = Account(username='hexylena', title='Helena')
# account = oe.add(account)
#
# # gh = AccountGithubDotCom(title='Helena', username='hexylena')
# # gh.update()
# # # Turned into a stored thing
# # gh = oe.add(gh)
# # account.data.sameAs = gh.ref()
#
# n = Note(title="baz", contents=[MarkdownBlock(author='gh/github.com/hexylena', contents="# Hello")])
# n.ensure_tag('status', LifecycleEnum.inprogress)
# st1 = StoredThing(data=n)
# st2 = StoredThing(data=Note(title="qux"))
# gb1.save_item(st1)
# gb2.save_item(st2)
#
# st1.data.title = "asdf"
# # oe.save_item(st1)
# oe.save()
#
# p = Project(title="HXPM")
# oe.add(p)
#
# f = File(title="logo.png", attachments=[UnresolvedReference(path="boshedron.png")])
# oe.add(f)
#
# f = File_S3(title="logo2.png", attachments=[UnresolvedReference(path="boshedron.png")])
# oe.add(f)
#
# dt = datetime.now()
# tz = ZoneInfo("Europe/Amsterdam")
# log = Log(title="Worked a bit", start_time=dt.astimezone(tz))
# oe.add(log)
#
# log.end_time = datetime.now().astimezone(tz)
# print(log)
#
# oe.save()
# print(p)
#
# oe.load()
# for f in oe.all():
#     print(repr(f))

print(bos.export("export2"))
