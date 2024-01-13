package main

import (
	// "fmt"
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
		n.NoteId = filename
		globalNotes.AddNote(n)
	}
}
