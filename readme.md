# Penemure

The project management system to replace all of the others.

> And pointed out to them every secret of their wisdom.
> He taught men to understand writing, and the use of ink and paper.

## Explicit Target Audience

Academic Weapons :sparkle:🔪

## User Stories

- I want to quickly add a task to be categorised later, I should just be able to write the title and be done, no other information required.
    - but when I want to go back and update a task it should be easy to attach it to a project/etc.
- I want to create a project
    - attach key files (agreement PDF, etc)
    - attach key members to the project in specific roles (andrew is the boss, helena is the PM, etc.)
    - sketch out some work packages
        - attach tasks to those WPs
        - assign people to those tasks
- I want to track a project, split it into subprojects (maybe work packages)
    - i'd like to add subtasks/subprojects
    - At relative dates from the start of the project / subproject (e.g. M1/Q1/Y1/Y1Q3)
    - And have those tasks repeat (e.g. Q2 every year.)
- I want to start a timer when I start working, it should record what I'm working on that I manually enter
    - when I switch tasks I'll enter the new task
    - maybe it should suggest a list of parent tasks it should be associated with?
    - and maybe I want to take some notes about what I worked on then

## Planned features

- [x] projects (v0)
    - [x] title (v0)
    - [x] description (v0)
    - [ ] roles (v0)
    - [ ] start/end dates (use this when showing date pickers) (v0)
    - [ ] key resources (docs/pdfs/logos/etc.) (v1)
    - [x] Child projects with own sharing (v1)
    - [ ] filter out blocked. (v0)
    - [ ] Views
        - [x] List (v0)
        - [ ] Timeline (v1)
        - [x] Kanban Board (v1)
        - [ ] Calendar (v1)
        - [ ] workflows (v2)
        - [x] dashboards with graphs (low) (v2)

- [x] tasks (v0)
    - [x] title (v0)
    - [x] description (v0)
    - [ ] start/end (exact or relative to project, e.g. M1/Q1) (v1)
    - [ ] Attachments/FILES (v0)
    - [x] tags (v0)
    - [x] assignees (v0)
    - [x] children (subtasks) (v0)
    - [x] blocking/blocked-by (v0)
    - [x] projects: multiple selection (v0)

- [ ] repeating tasks (v3)
    - [ ] daily/weekly/etc.
    - [ ] decide behaviour on completion/missing (does it just disappear? is it tracked?)
    - [ ] from a 'template'?
    - [ ] given a 'parent' task, does it generate subsequent ones? Are they real (existing on disk) or synthetic.
    - [ ] if we didn't want a 'full' version of properly calendered repeating events we could go for the 'cheap' version of schedule N future copies of this, without the ability to edit one/all future events
    - [ ] That's calendaring. That's just fucking calendaring, you're insane. stop it.

- [x] Time Tracking (v1)
    - [x] Easily enter a task and start it
    - [ ] Back date time
    - [x] associate to a specific task (one task can be made up of multiple time-management segments, maybe they're also conceptually 'tasks', just a 'quick subtask')

- [x] Server
    - [x] Using this from a folder sucks, it needs a permanently online server

- [ ] People
    - [ ] Allow assigning people without them existing in the system, just @ them. If a @{user} exists, use that for avatar/etc. (v0)

- [x] Teams
    - [x] Create arbitrary sub-groups of teams.

- [ ] Workflows
    - [ ] Move tasks around, modify them. Re-assign, etc. (v2)

- [ ] Forms
    - [ ] Basically simplified issue creation with mandatory fields. Really only needed on the 'hosting' server, less important locally. (v2)

- [ ] Import
    - [ ] import from calendar, generate an associated task that follows a calendar event around / can automatically have reminders.


## LICENSE

Licensed under [EUPL-1.2](./LICENSE.txt)
