from penemure.store import GitJsonFilesBackend, OverlayEngine, StoredThing
from penemure.note import Note, MarkdownBlock
from penemure.refs import UniformReference, UnresolvedReference
from penemure.apps import *
from penemure.main import *
from datetime import datetime
from zoneinfo import ZoneInfo

REPOS = os.environ.get('REPOS', '/home/user/projects/issues/:./pub').split(':')
bos = Penemure.discover(REPOS)
bos.load()

# for x in bos.overlayengine.all_blobs():
#     print(x)

for x in bos.overlayengine.all_things():
    # No tags originally, can just continue on.
    if len(x.thing.data.tags) == 0:
        continue
    if len(x.thing.data.tags_v2) != 0:
        continue

    # Not migrating templates
    if x.thing.data.type == 'template':
        continue

    print('## ' + x.thing.urn.urn)

    new_tags = []
    for tag in x.thing.data.tags:
        if tag.key == 'status':
            new_tags.append(StatusTag(key=tag.key, val=tag.val))
        elif tag.key == 'start_date':
            v = PastDateTimeTemplateTag.parse_val(tag.val)
            new_tags.append(PastDateTimeTag(key=tag.key, val=v))
        elif tag.key == 'end_date':
            v = PastDateTimeTemplateTag.parse_val(tag.val)
            new_tags.append(PastDateTimeTag(key=tag.key, val=v))
        elif tag.key == 'defense_date':
            v = PastDateTimeTemplateTag.parse_val(tag.val)
            new_tags.append(PastDateTimeTag(key=tag.key, val=v))
        elif tag.key == 'milestone':
            # find the associated milestone
            milestone = bos.overlayengine.search(type='milestone', title=tag.val)
            if len(milestone) == 0:
                raise Exception(f"Could not find milestone {tag.val}")
            milestone = milestone[0]
            new_tags.append(ReferenceTag(key=tag.key, val=milestone.thing.urn.urn))
        elif tag.key == 'cover':
            # find the associated milestone
            new_tags.append(ReferenceTag(key=tag.key, val=tag.val))
        elif tag.key == 'priority':
            new_tags.append(PriorityTag(key=tag.key, val=tag.val))
        elif tag.key == 'tags':
            new_tags.append(HashtagsTag(key=tag.key, val=HashtagsTemplateTag.parse_val(tag.val)))
        elif tag.key in ('page_path', 'template', 'locale', 'icon', 'description', 'url', 'yap level', 'CLASSIFICATION'):
            new_tags.append(TextTag(key=tag.key, val=tag.val))
        elif tag.key == 'progress':
            continue
        else:
            raise Exception(f"Unsupported {tag}")

    x.thing.data.tags_v2 = new_tags
    x.save()
