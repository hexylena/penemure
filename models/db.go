package models

import (
	"fmt"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	"os"
)

const (
	purple    = lipgloss.Color("99")
	gray      = lipgloss.Color("245")
	lightGray = lipgloss.Color("241")
)

type GlobalNotes struct {
	notes    map[string]Note
	modified bool
}

func (gn *GlobalNotes) Init() {
	gn.notes = make(map[string]Note)
	gn.modified = false
}

func (gn *GlobalNotes) GetNoteById(id string) Note {
	return gn.notes[id]
}

func (gn *GlobalNotes) GetIdByPartial(partial string) string {
	// Get all note ids
	noteIds := []string{}
	for _, note := range gn.notes {
		noteIds = append(noteIds, note.NoteId)
	}
	// Filter for those that match the partial
	matches := []string{}
	for _, noteId := range noteIds {
		// If it starts with
		if noteId[:len(partial)] == partial {
			matches = append(matches, noteId)
		}
	}
	switch len(matches) {
	case 0:
		panic("No matches found")
	case 1:
		return matches[0]
	default:
		panic("Multiple matches found")
	}
}

func (gn *GlobalNotes) DbSize() int {
	return len(gn.notes)
}

func (gn *GlobalNotes) GetNotes() map[string]Note {
	return gn.notes
}

func (gn *GlobalNotes) AddNote(n Note) {
	gn.notes[n.NoteId] = n
}

func NewGlobalNotes() GlobalNotes {
	gn := GlobalNotes{}
	gn.Init()
	return gn
}

func (gn *GlobalNotes) BubbleShow(id string) {
	note_id := gn.GetIdByPartial(id)
	note := gn.notes[note_id]
	note.BubblePrint()
}

func (gn *GlobalNotes) Edit(id string) {
	note_id := gn.GetIdByPartial(id)
	note := gn.notes[note_id]
	gn.notes[note_id] = note.Edit()
	gn.modified = true
}

func (gn *GlobalNotes) Unmodified() bool {
	return !gn.modified
}

func (gn *GlobalNotes) BubblePrint() {
	rows := [][]string{}
	for _, note := range gn.notes {
		rows = append(rows, []string{
			note.Type,
			note.Id(),
			note.Title,
			note.GetS("Status"),
			note.GetS("Tags"),
		})
	}

	re := lipgloss.NewRenderer(os.Stdout)
	var (
		// HeaderStyle is the lipgloss style used for the table headers.
		HeaderStyle = re.NewStyle().Foreground(purple).Bold(true).Align(lipgloss.Center)
		// CellStyle is the base lipgloss style used for the table rows.
		CellStyle = re.NewStyle().Padding(0, 1).Width(14)
		// OddRowStyle is the lipgloss style used for odd-numbered table rows.
		OddRowStyle = CellStyle.Copy().Foreground(gray)
		// EvenRowStyle is the lipgloss style used for even-numbered table rows.
		EvenRowStyle = CellStyle.Copy().Foreground(lightGray)
		// BorderStyle is the lipgloss style used for the table border.
		// BorderStyle = lipgloss.NewStyle().Foreground(purple)
	)

	t := table.New().
		Border(lipgloss.NormalBorder()).
		BorderStyle(lipgloss.NewStyle().Foreground(lipgloss.Color("99"))).
		StyleFunc(func(row, col int) lipgloss.Style {
			switch {
			case row == 0:
				return HeaderStyle
			case row%2 == 0:
				return EvenRowStyle
			default:
				return OddRowStyle
			}
		}).
		Headers("Type", "ID", "Title", "Status", "Tags").
		Rows(rows...)

	// You can also add tables row-by-row
	fmt.Println(t)
}
