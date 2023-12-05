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

- [ ] People
    - [ ] Allow assigning people without them existing in the system. (v0)

- [ ] Workflows
    - [ ] Move tasks around, modify them. Re-assign, etc. (v2)

- [ ] Forms
    - [ ] Basically simplified issue creation with mandatory fields. Really only needed on the 'hosting' server, less important locally. (v2)

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
