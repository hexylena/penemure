// Package adapter connects the tasks to storage
package adapter

import (
	pmm "github.com/hexylena/pm/models"
)

type TaskAdapter interface {
	LoadNotes(gn pmm.GlobalNotes)
	SaveNotes(gn pmm.GlobalNotes)
	DeleteNote(gn pmm.GlobalNotes, note_id pmm.NoteId)
}
