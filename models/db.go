package models

import (
	"fmt"
	"os"
	"golang.org/x/exp/maps"
	"regexp"
	"runtime/debug"
	"strconv"
	"strings"
	"text/template"
	"time"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	pmd "github.com/hexylena/pm/md"
	"github.com/hexylena/pm/sqlish"
)

const (
	purple    = lipgloss.Color("99")
	gray      = lipgloss.Color("245")
	lightGray = lipgloss.Color("241")
)

type GlobalNotes struct {
	notes map[NoteId]*Note
}

func (gn *GlobalNotes) Init() {
	gn.notes = make(map[NoteId]*Note)
}

func (gn *GlobalNotes) GetNoteById(id NoteId) *Note {
	return gn.notes[id]
}

func (gn *GlobalNotes) GetIdByPartial(partial PartialNoteId) (NoteId, error) {
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
		return "", fmt.Errorf("No matches found")
	case 1:
		return matches[0], nil
	default:
		return "", fmt.Errorf("Multiple matches found")
	}
}

func (gn *GlobalNotes) DbSize() int {
	return len(gn.notes)
}

func (gn *GlobalNotes) GetNotes() map[NoteId]*Note {
	return gn.notes
}

func (gn *GlobalNotes) GetTypes() []string {
	types := make(map[string]string)
	for _, note := range gn.notes {
		types[note.Type] = "";
	}

	return maps.Keys(types)
}

func (gn *GlobalNotes) GetNote(id NoteId) *Note {
	return gn.notes[id]
}

func (gn *GlobalNotes) GetNotesOfType(noteType string) map[NoteId]*Note {
	notes := make(map[NoteId]*Note)
	for _, note := range gn.notes {
		if note.Type == noteType {
			notes[note.NoteId] = note
		}
	}
	return notes
}

func (gn *GlobalNotes) DeleteNote(nid NoteId) {
	delete(gn.notes, nid)
}

func (gn *GlobalNotes) GetTopLevelNotes() map[NoteId]*Note {
	top_level_notes := make(map[NoteId]*Note)
	for _, note := range gn.notes {
		if len(note.Parents) == 0 {
			top_level_notes[note.NoteId] = note
		}
	}
	return top_level_notes
}

func (gn *GlobalNotes) GetTasks() map[NoteId]*Note {
	return gn.GetNotesOfType("task")
}

func (gn *GlobalNotes) GetLogs(open bool, closed bool) map[NoteId]*Note {
	notes := make(map[NoteId]*Note)
	for _, note := range gn.GetNotesOfType("log") {
		_, err := note.GetMetaKey("end_time")
		// Closed
		if err == nil {
			if closed {
				notes[note.NoteId] = note
			}
		} else {
			if open {
				notes[note.NoteId] = note
			}
		}
	}
	return notes
}

func (gn *GlobalNotes) GetOpenLog() *Note {
	for _, note := range gn.GetLogs(true, false) {
		return note
	}
	return nil
}

type AncestorType int

const (
	AT_Parent AncestorType = iota
)

func (gn *GlobalNotes) GetAncestorChain(note *Note, at_type AncestorType) []*Note {
	parents := []*Note{}
	parents = make([]*Note, 0)

	// type is either "parent" or "project"
	if at_type == AT_Parent {
		if len(note.Parents) > 0 {
			parent := gn.GetAncestorChain(gn.GetNoteById(note.Parents[0]), at_type)
			parents = append(parents, parent...)
		}
	}

	return parents
}

func (gn *GlobalNotes) GetPeople(note *Note) map[string]*Note {
	people := make(map[string]*Note)
	// loop over all notes for type == Person
	for _, note := range gn.notes {
		if note.Type == "person" {
			people[note.Title] = note
		}
	}
	return people
}

func (gn *GlobalNotes) GetUserAvatar(note *Note) string {
	if note.Type != "person" {
		return ""
	}

	// Check GetS for GitHub
	if note.GetS("github") != "" {
		return fmt.Sprintf("https://github.com/%s.png", note.GetS("github"))
	}

	// no avatar found
	return ""
}

// func (gn *GlobalNotes) GetProjectsForNote(note *Note) map[NoteId]*Note {
// 	projects := make(map[NoteId]*Note)
// 	for _, project := range note.Projects {
// 		projects[project] = gn.GetNoteById(project)
// 	}
// 	return projects
// }

func (gn *GlobalNotes) NoteHasChildren(note *Note) bool {
	for _, note := range gn.notes {
		if note.HasParent(note.NoteId) {
			return true
		}
	}
	return false
}

func (gn *GlobalNotes) GetChildren(note *Note) []*Note {
	logger.Debug("GetChildren", "note", note)
	children := []*Note{}
	for _, note := range gn.notes {
		if note.HasParent(note.NoteId) {
			children = append(children, note)
		}
	}
	return children
}

func (gn *GlobalNotes) GetProjects() map[NoteId]*Note {
	projects := make(map[NoteId]*Note)
	for _, note := range gn.notes {
		if note.Type == "project" {
			projects[note.NoteId] = note
		}
	}
	return projects
}

func (gn *GlobalNotes) AddNote(n Note) {
	gn.notes[n.NoteId] = &n
}

func NewGlobalNotes() GlobalNotes {
	logger.Debug("NewGlobalNotes")
	gn := GlobalNotes{}
	gn.Init()
	return gn
}

func (gn *GlobalNotes) BubbleShow(id PartialNoteId) {
	note_id, err := gn.GetIdByPartial(id)
	if err != nil {
		panic(err)
	}
	note := gn.notes[note_id]
	note.BubblePrint()
}

func (gn *GlobalNotes) QueryToHtml(query string) string {
	// SELECT id, title FROM tasks
	// SELECT id, title FROM tasks WHERE project = '4fca94d6-cdd9-4540-8b0e-6370eba448b7'
	// SELECT id, title FROM tasks WHERE project = '4fca94d6-cdd9-4540-8b0e-6370eba448b7' GROUP BY status
	// match by regex.

	logger.Info("tbl_view", "query", query)
	ans := sqlish.ParseSqlQuery(query)

	flattened_notes := []map[string]string{}
	for _, note := range gn.notes {
		flattened_notes = append(flattened_notes, note.Flatten())
	}

	results := ans.FilterDocuments(flattened_notes)

	// Render results as table
	html := "<table>"
	html += "<thead>"
	html += "<tr>"
	headers := ans.GetFields()
	for _, key := range headers {
		html += "<th>" + strings.ToTitle(key) + "</th>"
	}
	html += "</tr>"
	html += "<tbody>"

	for key, result := range results {
		header := "Results"
		if key != "__default__" {
			// Title Case, Capitalise Each Word
			header = strings.ToUpper(key[:1]) + key[1:]
			html += fmt.Sprintf("<tr><td colspan=\"%d\" style=\"text-align: center;background-color: #eee;\">%s</td></tr>", len(headers), header)
		}

		for _, row := range result {
			html += "<tr>"
			for i, cell := range row {
				html += "<td>" + gn.AutoFmt(headers[i], cell) + "</td>"
			}
			html += "</tr>"
		}
	}
	html += "</tbody>"
	html += "</table>"

	// todo? https://github.com/sidhant92/bool-parser-go
	// todo
	return html
}

func (gn *GlobalNotes) FmtTimeI(i int) string {
	t := time.Unix(int64(i), 0)
	return t.Format("2006-01-02 15:04:05")
}

func (gn *GlobalNotes) FmtTime(value string) string {
	i, err := strconv.ParseInt(value, 10, 64)
	if err != nil {
		panic(err)
	}
	t := time.Unix(i, 0)

	return t.Format("2006-01-02 15:04:05")
}

func (gn *GlobalNotes) AutoFmt(key, value string) string {
	// if it looks like a url, make it a link
	if strings.Contains(value, "http") {
		return "<a href=\"" + value + "\">" + value + "</a>"
	}

	uuid_regex := regexp.MustCompile(`^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$`)
	uuid_short := regexp.MustCompile(`^[a-f0-9]{8}$`)

	// if it looks like a uuid, by regex, make it a link
	if uuid_regex.MatchString(value) {
		return "<a href=\"" + value + ".html\">" + value + "</a>"
	}
	if uuid_short.MatchString(value) {
		note_id, err := gn.GetIdByPartial(PartialNoteId(value))
		if err != nil {
			panic(err)
		}
		full_value := fmt.Sprint(note_id)
		return "<a href=\"" + full_value + ".html\">" + value + "</a>"
	}

	if key == "created" || key == "modified" || key == "start_time" || key == "end_time" {
		gn.FmtTime(value)
	}

	// if key == "author" || key == "Assignee" || key == "owner" {
	// 	gn.GetUserAvatar
	// }

	return value
}

func (gn *GlobalNotes) Edit(id PartialNoteId) {
	note_id, err := gn.GetIdByPartial(id)
	if err != nil {
		panic(err)
	}
	note := gn.notes[note_id]
	newnote := note.Edit()
	gn.notes[note_id] = &newnote
}

func (gn *GlobalNotes) Export() {
	// Create export/ directory if it doesn't exist
	if _, err := os.Stat("./export"); os.IsNotExist(err) {
		os.Mkdir("./export", 0755)
	}

	// Read template from templates/note.html
	list_tpl_text, err := os.ReadFile("templates/list.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}
	list_tpl, err := template.New("list").Parse(string(list_tpl_text))
	if err != nil {
		logger.Error("Error", "err", err)
	}

	// Render template
	f, err := os.Create("export/index.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}

	err = list_tpl.Execute(f, gn)
	if err != nil {
		logger.Error("Error", "err", err)
	}

	// Export individual notes
	for _, note := range gn.notes {
		note.ExportToFile(gn)
	}
}

func (gn *GlobalNotes) VcsRev(len int) string {
	info, ok := debug.ReadBuildInfo()
	if !ok {
		return ""
	}
	for _, kv := range info.Settings {
		if kv.Key == "vcs.revision" {
			return kv.Value[:len]
		}
	}
	return ""
}

func (gn *GlobalNotes) NewEdit() {
	note := NewNote()
	gn.RegisterNote(note)
	partial := PartialNoteId(fmt.Sprint(note.NoteId))
	gn.Edit(partial)
}

func (gn *GlobalNotes) RegisterNote(n *Note) {
	n.modified = true
	gn.notes[n.NoteId] = n
}

func (gn *GlobalNotes) BubblePrint() {
	rows := [][]string{}
	for _, note := range gn.notes {
		rows = append(rows, []string{
			note.Type,
			note.Id(),
			note.Title,
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
		Headers("Type", "ID", "Title", "Parents", "Status", "Tags").
		Rows(rows...)

	// You can also add tables row-by-row
	fmt.Println(t)
}

func (gn *GlobalNotes) BlockToHtml(b pmd.SyntaxNode) string {
	return b.Html()
}

func (gn *GlobalNotes) BlockToHtml3(b pmd.SyntaxNode) string {
	if b.Type() == pmd.TABLE_VIEW {
		b := b.(*pmd.TableView)
		return gn.QueryToHtml(b.Query)
	}
	return b.Html()
}
