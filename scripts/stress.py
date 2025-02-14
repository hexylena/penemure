from penemure.store import *
from penemure.note import *
from penemure.refs import *
from penemure.apps import *
from penemure.main import *
import argparse
import random


parser = argparse.ArgumentParser(
                    prog='PENEMURE-STRESS',
                    description='Generate a stress test')
parser.add_argument('folder', type=str)
parser.add_argument('-n', type=int, help='Number of notes to generate', default=500)
args = parser.parse_args()


BaseBackend.new_meta(args.folder, name='stress test', description='too many notes', icon='⚠️')
# TODO: must manually initialise git?
subprocess.check_call(['git', 'init'], cwd=args.folder)
subprocess.check_call(['git', 'add', 'meta.json'], cwd=args.folder)
subprocess.check_call(['git', 'commit', '-m', 'init'], cwd=args.folder)

be = GitJsonFilesBackend.discover(args.folder)
pen = Penemure(backends=[be])

from faker import Faker
faker = Faker(['nl_NL', 'en_US', 'zh_CN'])

notes = []
for i in range(args.n):
    n = random.random()
    if n < 0.1:
        note = Note(title=faker.text(max_nb_chars=30), type='log')
        note.contents = []
        note.add_tag(Tag(key='start_date', val=str(time.time())))
        note.add_tag(Tag(key='end_date', val=str(time.time())))
    elif n < 0.4:
        note = Note(title=faker.text(max_nb_chars=30), type='project')
        note.add_tag(Tag(key='milestone', val=random.choice('123456789')))
        note.add_tag(Tag(key='description', val=faker.text(max_nb_chars=50)))
        note.contents = []
    else:
        note = Note(title=faker.name())
        note.contents = []

    for i in range(random.randint(0, 20)):
        md = MarkdownBlock(contents=faker.text(max_nb_chars=random.randint(20, 500)),
                           author=UniformReference.from_string('urn:penemure:account:hexylena'),
                           type='markdown'
                           )
        note.contents.append(md)
    pen.overlayengine.add(note)

pen.save()
pen.load()

notes = pen.overlayengine.all()

for i in range(10):
    parents = random.choices(notes, k=args.n // 20)
    children = random.choices(notes, k=args.n // 5)

    print([x.thing.urn.urn for x in parents])
    for n in children:
        if n.thing.data.parents is None:
            n.thing.data.parents = []
        n.thing.data.parents.append(random.choice(parents).thing.urn)
        print(n.thing.data.parents)
        pen.overlayengine.save_thing(n, fsync=False)

pen.save()
# for note in pen.overlayengine.all():
#     print(note.thing.urn.urn)
