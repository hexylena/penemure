package main

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
	"os"
	"path/filepath"
)

func FilePathWalkDir(root string) ([]string, error) {
	var files []string
	err := filepath.Walk(root, func(path string, info os.FileInfo, err error) error {
		if !info.IsDir() {
			files = append(files, path)
		}
		return nil
	})
	return files, err
}

func LoadNotes() {
	// Load all notes from the notes directory
	// glob
	paths, err := FilePathWalkDir("./projects")
	if err != nil {
		panic(err)
	}
	for _, path := range paths {
		n := pmm.Note{}
		n.ParseNote(path)
		// Get filename component of path
		filename := filepath.Base(path)
		n.NoteId = pmm.NoteId(filename)

		globalNotes.AddNote(n)
	}
}

func id2path(id pmm.NoteId) string {
	return fmt.Sprintf("./projects/%s/%s/%s", id[:1], id[1:2], id)
}

func SaveNotes() {
	// Save all notes to the notes directory
	for _, note := range globalNotes.GetNotes() {
		if note.IsModified() {
			fmt.Println("Saving note", note.Title, "to", id2path(note.NoteId))
			fmt.Println(note)
			note.SaveNote(id2path(note.NoteId))
		}
	}
}
