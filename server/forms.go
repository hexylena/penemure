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
		}
	}

	if ok := formData["project"]; len(ok) > 0 {
		fmt.Println("PROJECTSSSS ", ok)
		note.SetParentsFromIds(ok)
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

	if ok := formData["notes"]; len(ok) > 0 {
		text := formData["notes"][0]
		note.Blocks = pmd.MdToBlocks([]byte(text))
	}

	// Update where relevant
	note.Type = "log"

	fmt.Println("form", formData, "note", note)

	gn.RegisterNote(note)
	(*ga).SaveNotes(*gn)
}

func processNoteSubmission(formData url.Values) *pmm.Note {
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

	if ok := formData["project"]; len(ok) > 0 {
		note.SetParentsFromIds(ok)
	}

	if ok := formData["type"]; len(ok) > 0 {
		note.Type = ok[0]
	}

	if ok := formData["name"]; len(ok) > 0 {
		note.Title = ok[0]
	}

	if ok := formData["tags"]; len(ok) > 0 {
		note.ClearTags()
		for _, tag := range ok {
			note.AddTag(tag)
		}
	}

	if ok := formData["m_type"]; len(ok) > 0 {
		// zero out our data initially
		note.Meta = make([]*pmm.Meta, len(ok))
		for i, m := range ok {
			note.Meta[i] = &pmm.Meta{
				Type:  m,
				Icon:  formData["m_icon"][i],
				Value: formData["m_valu"][i],
				Title: formData["m_titl"][i],
			}
		}
	}

	if ok := formData["notes"]; len(ok) > 0 {
		note.Blocks = pmd.MdToBlocks([]byte(ok[0]))
	}

	gn.RegisterNote(note)
	(*ga).SaveNotes(*gn)
	return note
}
