# Helena's Task Tracking System

the one system to replace all of the rest. (ofc it's not, it's just option #15.)

## Explicit Target Audience

AuDHD Academics :sparkle: (in general just overwhelmed academics with wishlists and deadlines.)

## Required features

- [ ] projects (v0)
    - [ ] title (v0)
    - [ ] description (v0)
    - [ ] roles (v0)
    - [ ] start/end dates (use this when showing date pickers) (v0)
    - [ ] key resources (docs/pdfs/logos/etc.) (v1)
    - [ ] Child projects with own sharing (v1)
    - [ ] filter out blocked. (v0)
    - [ ] Groups of Tasks - what did she mean by this? The world will never know.
    - [ ] Views
        - [ ] List (v0)
        - [ ] Timeline (v1)
        - [ ] Board (v1)
        - [ ] Calendar (v1)
        - [ ] workflows (v2)
        - [ ] dashboards (low) (v2)

- [ ] tasks (v0)
    - [ ] title (v0)
    - [ ] description (v0)
    - [ ] start/end (exact or relative to project, e.g. M1/Q1) (v0)
    - [ ] tags (v0)
    - [ ] assignees (v0)
    - [ ] children (subtasks) (v0)
    - [ ] blocking/blocked-by (v0)
    - [ ] projects: multiple selection (v0)
    - [ ] in project: Group of Tasks - ibid, does it mean like, lists within a project? can this be modelled as a task?

- [ ] repeating tasks
    - [ ] daily/weekly/etc.
    - [ ] decide behaviour on completion/missing (does it just disappear? is it tracked?)
    - [ ] from a 'template'?
    - [ ] given a 'parent' task, does it generate subsequent ones? Are they real (existing on disk) or synthetic.
    - [ ] if we didn't want a 'full' version of properly calendered repeating events we could go for the 'cheap' version of schedule N future copies of this, without the ability to edit one/all future events

- [ ] Time Tracking (v1)
    - [ ] Easily enter a task and start it
    - [ ] Back date time
    - [ ] associate to a specific task (one task can be made up of multiple time-management segments, maybe they're also conceptually 'tasks', just a 'quick subtask')

- [ ] People
    - [ ] Allow assigning people without them existing in the system. (v0)

- [ ] Teams
    - [ ] Create arbitrary sub-groups of teams.

- [ ] Workflows
    - [ ] Move tasks around, modify them. Re-assign, etc. (v2)

- [ ] Forms
    - [ ] Basically simplified issue creation with mandatory fields. Really only needed on the 'hosting' server, less important locally. (v2)

## User Stories

- I want to track a project, split it into subprojects (maybe work packages)
    - i'd like to add subtasks
    - At relative dates from the start of the project / subproject (e.g. M1/Q1/Y1/Y1Q3)
    - And have those tasks repeat (e.g. Q2 every year.)
- I want to start a timer when I start working, it should record what I'm working on that I manually enter
    - when I switch tasks I'll enter the new task
    - maybe it should suggest a list of parent tasks it should be associated with?
- Grocery list
- Daily habits/chores

## System Design

### Git Based

Consider taking from [git-bug's](https://github.com/MichaelMure/git-bug/blob/master/doc/model.md)
model which meets the non-goals of offline-first, fast local experiences which
isn't really part of most project management tools but would make my boss happy
(and me.)

I want a system that's basically built on git, so that we can have the entire
system shared with everyone involved, automatically.

Initially it'll only support a single repository, you'll just go into that repo
and manage issues/bugs/etc for that repo.

Long term, additionally there will be a 'server' component that exposes it to
the world with configurable authentication, (and a local version of that server
that runs without that auth.)

I think the AuthZ should be offloaded to your git host, if you have permission
to clone a repo, you have permission to modify all the issues in it, access
everything. Want to delegate only a sub-set of tasks? Great, put them in a
separate repo.

How do you see all your tasks in the future? That's where the server comes in, once that's
written you'll list your projects that are using this system, and it'll
aggregate everything you can access in one nice display. 

### Internal Structure

Is it possible (useful?) to make this recursive? Tasks all the way down with different flavours of tasks?

```
project (it's a task!)
└── list/group of tasks (It's also a task!)
    └── task
        └── (sub)task
            └── ...
```

yeah that actually sounds sensible weirdly.

### Data Model

```yaml
id: 6af26813-27e6-4f6b-9f20-324320a7d923
title: My Page
_meta:
  icon: 0.png
_tags:
  - title: URL
    icon: 1.png
    type: text
    value: https://example.com
  - title: Asignee
    icon: 1.png
    type: people
    values: [jane, bob, @f90db3bd-0fee-4320-855d-7ec3451f48dc]
  - title: Parent
    type: link
    values: [@8c7b8634-445b-4efc-894c-314030ae0e16]
_blocks:
 - type: h1
   contents: blah
 - type: p
   contents: blah
```

#### Types

markdown:

- h1/2/3 {4/5/6}
- todo list (automatically registers as sub-tasks
- table
- bullet/numbered
- details/summary
- blockquote
- code
- divider
- TeX

advanced:

- url (link preview?)
- image
- file

database links/queries:

- table
- kanban board
- gallery
- list
- calendar
- timeline

misc:

- breadcrumbs
- 2/3/4/5 columns
- mermaid
- link to person/page/date
- @ a day/time, and then have that show up in queries somehow????
- embed pdf

## Roadmap

- v0 - schemas that can be edited by shitty cli tools so we can get *something* functional.
- v1 - git-bug backing, so they can be synced
- v2 - the server implementation

## CLI

iT's CRUDdy bAbY

```
pm project list
pm project add
pm project remove <id>
pm project edit <id>
pm project show <id>
pm task list
pm task add
pm task remove <id>
pm task edit <id>
pm task show <id>
```
