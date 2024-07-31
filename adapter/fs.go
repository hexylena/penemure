package adapter

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
	pml "github.com/hexylena/pm/log"
	"os"
	"path/filepath"
)

type FsAdapter struct {
	Path string
}

func (a *FsAdapter) filePathWalkDir(root string) ([]string, error) {
	var files []string
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if !info.IsDir() {
			files = append(files, path)
		}
		return nil
	})
	return files, err
}

func (a *FsAdapter) LoadNotes(gn pmm.GlobalNotes) {
	pml.L("adapter").Info("LoadNotes")
	// Load all notes from the notes directory
	// glob
	paths, err := a.filePathWalkDir(a.Path)
	if err != nil {
		panic(err)
	}
	for _, path := range paths {
		n := pmm.Note{}
		n.ParseNote(path)
		// Get filename component of path
		filename := filepath.Base(path)
		n.NoteId = pmm.NoteId(filename)
		gn.AddNote(n)
	}
}

func (a *FsAdapter) id2path(id pmm.NoteId) string {
	return fmt.Sprintf("%s/%s/%s/%s", a.Path, id[:1], id[1:2], id)
}

func (a *FsAdapter) SaveNotes(gn pmm.GlobalNotes) {
	pml.L("adapter").Info("SaveNotes")
	// Save all notes to the notes directory
	for _, note := range gn.GetNotes() {
		if note.IsModified() {
			pml.L("adapter").Info("SaveNotes", "note", note.Title, "id", note.NoteId)
			note.SaveNote(a.id2path(note.NoteId))
		}
	}
}

func (a *FsAdapter) DeleteNote(gn pmm.GlobalNotes, note_id pmm.NoteId) {
	gn.DeleteNote(note_id)

	err := os.Remove(a.id2path(note_id))
	if err != nil {
		fmt.Println(err)
	}
}

