package server

import (
	"fmt"
	"net/url"
	"strconv"
	"strings"
	"time"

	pmd "github.com/hexylena/pm/md"
	pmm "github.com/hexylena/pm/models"
)

func processTimeSubmission(formData url.Values) {
	var note *pmm.Note
	if ok := formData["note_id"]; len(ok) > 0 {
		partial := pmm.PartialNoteId(ok[0])
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			note = pmm.NewNote()
			logger.Info("Could not find note", "note_id", note_id)
		} else {
			note = gn.GetNoteByID(note_id)
			logger.Info("Found note", "note", note)
		}
	} else {
		note = pmm.NewNote()
		logger.Info("New note!")
	}

	if ok := formData["action"]; len(ok) > 0 {
		switch formData["action"][0] {
		case "start":
			logger.Info("Starting task")
			note.AddMeta("time", "start_time", strconv.FormatInt(time.Now().Unix(), 10))
		case "stop":
			logger.Info("Stopping task")
			note.AddMeta("time", "end_time", strconv.FormatInt(time.Now().Unix(), 10))
		case "notes":
			text := formData["notes"][0]
			note.Blocks = pmd.MdToBlocks([]byte(text))
		}
	}

	if ok := formData["project_id"]; len(ok) > 0 {
		project_ids := strings.Split(formData["project_id"][0], ",")
		note.SetParentsFromIds(project_ids)
	}

	if ok := formData["name"]; len(ok) > 0 {
		name := formData["name"][0]
		note.Title = name
	}

	if ok := formData["tags"]; len(ok) > 0 {
		tags := strings.Split(formData["tags"][0][1:], ",")
		for _, tag := range tags {
			note.AddTag(tag)
		}
	}

	// Update where relevant
	note.Type = "log"

	fmt.Println("form", formData, "note", note)

	gn.RegisterNote(note)
	(*ga).SaveNotes(*gn)
}

func processNoteSubmission(formData url.Values) {
	var note *pmm.Note
	if ok := formData["note_id"]; len(ok) > 0 {
		partial := pmm.PartialNoteId(ok[0])
		note_id, err := gn.GetIdByPartial(partial)
		if err != nil {
			note = pmm.NewNote()
			logger.Info("Could not find note", "note_id", note_id)
		} else {
			note = gn.GetNoteByID(note_id)
			logger.Info("Found note", "note", note)
		}
	} else {
		note = pmm.NewNote()
		logger.Info("New note!")
	}

	if ok := formData["project_id"]; len(ok) > 0 {
		project_ids := strings.Split(formData["project_id"][0], ",")
		note.SetParentsFromIds(project_ids)
	}

	if ok := formData["type"]; len(ok) > 0 {
		note.Type = formData["type"][0]
	}

	if ok := formData["name"]; len(ok) > 0 {
		note.Title = formData["name"][0]
	}

	if ok := formData["tags"]; len(ok) > 0 {
		if len(formData["tags"][0]) > 0 {
			tags := strings.Split(formData["tags"][0][1:], ",")
			for _, tag := range tags {
				note.AddTag(tag)
			}
		}

	}

	fmt.Println("form", formData, "note", note)

	gn.RegisterNote(note)
	(*ga).SaveNotes(*gn)
}
