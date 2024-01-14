package models

import (
	"fmt"
	"os"
	"text/template"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
)

const (
	purple    = lipgloss.Color("99")
	gray      = lipgloss.Color("245")
	lightGray = lipgloss.Color("241")
)

type GlobalNotes struct {
	notes    map[NoteId]*Note
	modified bool
}

func (gn *GlobalNotes) Init() {
	gn.notes = make(map[NoteId]*Note)
	gn.modified = false
}

func (gn *GlobalNotes) GetNoteById(id NoteId) *Note {
	return gn.notes[id]
}

func (gn *GlobalNotes) GetIdByPartial(partial PartialNoteId) NoteId {
	s_partial := fmt.Sprint(partial)

	// Get all note ids
	noteIds := []NoteId{}
	for _, note := range gn.notes {
		noteIds = append(noteIds, note.NoteId)
	}
	// Filter for those that match the partial
	matches := []NoteId{}
	for _, noteId := range noteIds {
		// If it starts with
		if fmt.Sprint(noteId)[:len(s_partial)] == s_partial {
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

func (gn *GlobalNotes) GetNotes() map[NoteId]*Note {
	return gn.notes
}

func (gn *GlobalNotes) AddNote(n Note) {
	gn.notes[n.NoteId] = &n
}

func NewGlobalNotes() GlobalNotes {
	gn := GlobalNotes{}
	gn.Init()
	return gn
}

func (gn *GlobalNotes) BubbleShow(id PartialNoteId) {
	note_id := gn.GetIdByPartial(id)
	note := gn.notes[note_id]
	note.BubblePrint()
}

func (gn *GlobalNotes) Edit(id PartialNoteId) {
	note_id := gn.GetIdByPartial(id)
	note := gn.notes[note_id]
	newnote := note.Edit()
	gn.notes[note_id] = &newnote
	gn.modified = true
}

func (gn *GlobalNotes) Export() {
	// Create export/ directory if it doesn't exist
	if _, err := os.Stat("./export"); os.IsNotExist(err) {
		os.Mkdir("./export", 0755)
	}

	// Read template from templates/note.html
	list_tpl_text, err := os.ReadFile("templates/list.html")
	if err != nil {
		fmt.Println(err)
	}
	list_tpl, err := template.New("list").Parse(string(list_tpl_text))
	if err != nil {
		fmt.Println(err)
	}

	// Render template
	f, err := os.Create("export/index.html")
	if err != nil {
		fmt.Println(err)
	}

	err = list_tpl.Execute(f, gn)
	if err != nil {
		fmt.Println(err)
	}

	// Export individual notes
	for _, note := range gn.notes {
		note.Export(gn)
	}
}

func (gn *GlobalNotes) NewEdit() {
	note := NewNote()
	gn.notes[note.NoteId] = note
	partial := PartialNoteId(fmt.Sprint(note.NoteId))
	gn.Edit(partial)
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
			fmt.Sprintf("%s", note.Projects),
			fmt.Sprintf("%s", note.Parents),
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
		Headers("Type", "ID", "Title", "Projects", "Parents", "Status", "Tags").
		Rows(rows...)

	// You can also add tables row-by-row
	fmt.Println(t)
}
