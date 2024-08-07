// Package models provides functionality for working with models.
package models

import (
	"embed"
	"fmt"
	"io/fs"
	"os"
	"path"
	"regexp"
	"runtime/debug"
	"sort"
	"strconv"
	"strings"
	"text/template"
	"time"

	"golang.org/x/exp/maps"

	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	pmc "github.com/hexylena/pm/config"
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

func (gn *GlobalNotes) GetNoteByID(id NoteId) *Note {
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
		types[note.Type] = ""
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

func (gn *GlobalNotes) GetNotesOfTypes(noteTypes []string) map[NoteId]*Note {
	notes := make(map[NoteId]*Note)
	for _, note := range gn.notes {
		for _, noteType := range noteTypes {
			if note.Type == noteType {
				notes[note.NoteId] = note
			}
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

type structuredLog struct {
	Date time.Time
	Logs []*Note
}

func GroupByProperty[T any, K comparable](items []T, getProperty func(T) K) map[K][]T {
	grouped := make(map[K][]T)

	for _, item := range items {
		key := getProperty(item)
		grouped[key] = append(grouped[key], item)
	}

	return grouped
}

func (gn *GlobalNotes) GetStructuredLogs() []structuredLog {
	logsm := gn.GetLogs(false, true)
	logs := make([]*Note, 0)
	for _, n := range logsm {
		logs = append(logs, n)
	}

	groupedByDay := GroupByProperty(logs, func(n *Note) string {
		d, _ := n.GetStartEndTime("start")
		df := d.Format("2006-01-02")
		return df
	})

	// access keys in sorted manner
	keys := maps.Keys(groupedByDay)
	sort.Strings(keys)

	out := make([]structuredLog, 0)

	for i := len(keys) - 1; i >= 0; i-- {
		key := keys[i]
		// Access the key and its corresponding value
		value := groupedByDay[key]

		sort.Slice(value, func(i, j int) bool {
			return value[i].CreatedAt > value[j].CreatedAt
		})

		d, _ := value[0].GetStartEndTime("start")
		out = append(out, structuredLog{d, value})
		// Your code here
	}
	return out
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
	parents := make([]*Note, 0)

	// type is either "parent" or "project"
	if at_type == AT_Parent {
		if len(note.Parents) > 0 {
			parent := gn.GetAncestorChain(gn.GetNoteByID(note.Parents[0]), at_type)
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

// func (gn *GlobalNotes) NoteHasChildren(note *Note) bool {
// 	for _, note := range gn.notes {
// 		if note.HasParent(note.NoteId) {
// 			return true
// 		}
// 	}
// 	return false
// }

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

func (gn *GlobalNotes) GetProjectsAndTasks(note *Note) []*Note {
	logger.Debug("GetChildren", "note", note)
	children := []*Note{}
	for _, note := range gn.notes {
		if note.HasParent(note.NoteId) {
			children = append(children, note)
		}
	}
	return children
}

func (gn *GlobalNotes) Mappify(notes []*Note) map[NoteId]*Note {
	res := make(map[NoteId]*Note)
	for _, note := range gn.notes {
		res[note.NoteId] = note
	}
	return res
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

func (gn *GlobalNotes) QueryToHtml(query, display string) string {
	// SELECT id, title FROM tasks
	// SELECT id, title FROM tasks WHERE project = '4fca94d6-cdd9-4540-8b0e-6370eba448b7'
	// SELECT id, title FROM tasks WHERE project = '4fca94d6-cdd9-4540-8b0e-6370eba448b7' GROUP BY status
	// match by regex.

	logger.Info("tbl_view", "query", query)
	ans := sqlish.ParseSqlQuery(query)

	flattened_notes := []map[string]string{}
	for _, note := range gn.notes {
		flattened_notes = append(flattened_notes, note.Flatten())
		// gross! :D
		flattened_notes[len(flattened_notes)-1]["title"] = fmt.Sprintf(`<a href="%s.html">%s %s</a>`, note.NoteId, note.GetIconHtml(), note.Title)
	}
	results := ans.FilterDocuments(flattened_notes)
	switch display {
	case "kanban":
		return gn.QueryDisplayKanban(ans, results)
	case "list":
		return gn.QueryDisplayList(ans, results)
	default:
		return gn.QueryDisplayTable(ans, results)
	}

}

func (gn *GlobalNotes) QueryDisplayTable(ans *sqlish.SqlLikeQuery, results *sqlish.GroupedResultSet) string {
	// Render results as table
	html := "<table>\n"
	html += "<thead>\n"
	html += "<tr>"
	headers := ans.GetFields()
	col_count := 0
	for _, key := range headers {
		html += "<th>" + strings.ToTitle(key) + "</th>"
		col_count++
	}
	html += "</tr>\n"
	html += "<tbody>"

	for key, result := range results.Rows {
		header := "Results"
		if key != "__default__" {
			// Title Case, Capitalise Each Word
			header = strings.ToUpper(key[:1]) + key[1:]
			html += fmt.Sprintf("<tr><td colspan=\"%d\" class=\"header\">%s</td></tr>", len(headers), header)
		}

		for _, row := range result {
			html += "<tr>"
			for i, cell := range row {
				if cell == "" {
					html += "<td></td>"
					// TODO: this fixes it being run through autofmt twice, but, that shouldn't've happened in the first place.
				} else if cell[0] == '<' {
					html += "<td>" + cell + "</td>"
				} else {
					html += "<td>" + gn.AutoFmt(headers[i], cell) + "</td>"
				}
			}
			html += "</tr>\n"
		}
	}
	html += "</tbody>"
	// html += fmt.Sprintf(`<tfoot><tr><td colspan="%d" class="query">Query: <code>%s</code></td></tr></tfoot>`, col_count, query)
	html += "</table>"

	// todo? https://github.com/sidhant92/bool-parser-go
	// todo
	return html
}

func (gn *GlobalNotes) QueryDisplayList(ans *sqlish.SqlLikeQuery, results *sqlish.GroupedResultSet) string {
	// Render results as table
	html := ""
	headers := ans.GetFields()

	for key, result := range results.Rows {
		header := "Results"
		if key != "__default__" {
			// Title Case, Capitalise Each Word
			header = strings.ToUpper(key[:1]) + key[1:]
			html += fmt.Sprintf("<b>%s</b>", header)
		}
		html += "<ul>"
		for _, row := range result {
			html += "<li>"
			hrow := make([]string, 0)
			for i, cell := range row {
				if cell == "" {
					// TODO: this fixes it being run through autofmt twice, but, that shouldn't've happened in the first place.
					hrow = append(hrow, "")
				} else if cell[0] == '<' {
					hrow = append(hrow, cell)
				} else {
					hrow = append(hrow, gn.AutoFmt(headers[i], cell))
				}
			}
			html += strings.Join(hrow, ", ")
			html += "</li>\n"
		}
		html += "</ul>"
	}
	return html
}

func (gn *GlobalNotes) QueryDisplayKanban(ans *sqlish.SqlLikeQuery, results *sqlish.GroupedResultSet) string {
	// Render results as table
	html := "<div class=\"kanban\">\n"
	headers := ans.GetFields()

	for key, result := range results.Rows {
		html += `<div class="kanban-column">`

		header := "Results"
		if key != "__default__" {
			// Title Case, Capitalise Each Word
			header = strings.ToUpper(key[:1]) + key[1:]
			html += fmt.Sprintf(`<div class="title">%s</div>`, header)
		}

		for _, row := range result {
			html += `<div class="card">`
			for i, cell := range row {
				if cell == "" {
					html += "<span></span>"
					// TODO: this fixes it being run through autofmt twice, but, that shouldn't've happened in the first place.
				} else if cell[0] == '<' {
					html += "<div>" + cell + "</div>"
				} else {
					html += "<div>" + gn.AutoFmt(headers[i], cell) + "</div>"
				}
			}
			html += "</div>\n"
		}
		html += `</div>`
	}
	html += "</div>"
	return html
}
func (gn *GlobalNotes) FmtTimeI(i int) string {
	t := time.Unix(int64(i), 0)
	return t.Format("2006-01-02 15:04:05")
}

func (gn *GlobalNotes) FmtTime(value string) string {
	if value == "" {
		return ""
	}
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

	// references
	reference := regexp.MustCompile(`^@[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$`)
	if reference.MatchString(value) {
		note_id := gn.GetNoteByID(NoteId(value[1:]))
		// todo different icon for person references.
		// fmt.Println(note_id.GetIconHtml())
		return fmt.Sprintf(`<a href="%s.html">%s %s</a>`, note_id.NoteId, note_id.GetIconHtml(), note_id.Title)
	}

	if key == "created" || key == "modified" || key == "start_time" || key == "end_time" {
		return gn.FmtTime(value)
	}

	// if key == "author" || key == "Assignee" || key == "owner" {
	// 	gn.GetUserAvatar
	// }

	return value
}

func (gn *GlobalNotes) AutoFmtMeta(m Meta) string {
	// logger.Info("AutoFmtMeta", "m", m)
	// value is a []interface{} or interface{}, check which:
	switch m.Value.(type) {
	case []interface{}:
		// if it's a list, join them with a comma
		res := ""
		for _, v := range m.Value.([]interface{}) {
			res += gn.AutoFmt(m.Title, v.(string)) + ", "
		}
		return res[:len(res)-2]
	case interface{}:
		return gn.AutoFmt(m.Title, m.Value.(string))
	}
	return gn.AutoFmt(m.Title, m.Value.(string))
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

func (gn *GlobalNotes) exportTemplate(s string, config *pmc.HxpmConfig, templateFS *embed.FS) {
	type templateContext2 struct {
		Gn     *GlobalNotes
		Config *pmc.HxpmConfig
	}

	f_search, err := os.Create(path.Join(config.ExportDirectory, fmt.Sprintf("%s.html", s)))
	if err != nil {
		logger.Error("Error", "err", err)
	}
	search_tmpl, err := template.New("").ParseFS(
		templateFS,
		fmt.Sprintf("templates/%s.html", s),
		"templates/base.html",
	)
	if err != nil {
		logger.Error("Error", "err", err)
	}
	err = search_tmpl.ExecuteTemplate(f_search, "base", templateContext2{gn, config})
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

func (gn *GlobalNotes) Export(config *pmc.HxpmConfig, templateFS *embed.FS) {
	// Create export/ directory if it doesn't exist
	if _, err := os.Stat(config.ExportDirectory); os.IsNotExist(err) {
		os.Mkdir(config.ExportDirectory, 0755)
	}

	tmpl, err := template.New("").ParseFS(templateFS, "templates/list.html", "templates/base.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}

	// Render template
	f, err := os.Create(path.Join(config.ExportDirectory, "index.html"))
	if err != nil {
		logger.Error("Error", "err", err)
	}

	type templateContext2 struct {
		Gn     *GlobalNotes
		Config *pmc.HxpmConfig
	}

	err = tmpl.ExecuteTemplate(f, "base", templateContext2{gn, config})
	if err != nil {
		logger.Error("Error", "err", err)
	}
	// Export individual notes
	for _, note := range gn.notes {
		note.ExportToFile(gn, config)
	}

	// Copy templates/assets into export
	static, err := getAllFilenames(templateFS)
	if err != nil {
		logger.Error("Could not list files in embedded FS")
	}
	for _, fn := range static {
		if !strings.Contains(fn, "assets") {
			continue
		}
		// write to config.exportdirectory
		fileData, err := templateFS.ReadFile(fn)
		if err != nil {
			logger.Error("Error reading file", "file", fn, "err", err)
			continue
		}
		outputPath := path.Join(config.ExportDirectory, strings.TrimPrefix(fn, "templates/"))
		outputDir := path.Dir(outputPath)
		logger.Info("Creating dir", "dir", outputDir)
		err = os.MkdirAll(outputDir, 0755)

		if err != nil {
			logger.Error("Error creating directory", "dir", outputDir, "err", err)
		}

		err = os.WriteFile(outputPath, fileData, 0644)
		if err != nil {
			logger.Error("Error writing file", "file", outputPath, "err", err)
		}
	}

	// Export search page
	gn.exportTemplate("search", config, templateFS)
	gn.exportTemplate("404", config, templateFS)

	manifest := config.Manifest()
	// save to export/manifest.json
	manifestFile := path.Join(config.ExportDirectory, "manifest.json")
	err = os.WriteFile(manifestFile, manifest, 0644)
	if err != nil {
		logger.Error("Error", "err", err)
	}
}

// https://gist.github.com/clarkmcc/1fdab4472283bb68464d066d6b4169bc
func getAllFilenames(efs *embed.FS) (files []string, err error) {
	if err := fs.WalkDir(efs, ".", func(path string, d fs.DirEntry, err error) error {
		if d.IsDir() {
			return nil
		}

		files = append(files, path)

		return nil
	}); err != nil {
		return nil, err
	}

	return files, nil
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
	if b.Type() == pmd.TABLE_VIEW {
		b := b.(*pmd.TableView)
		return gn.QueryToHtml(b.Query, b.Display)
	}
	return b.Html()
}

func (gn *GlobalNotes) GetChildrenFormatted(note NoteId) string {
	return gn.QueryToHtml("select title, created, Author from notes where parent = '"+string(note)+"' group by type order by created ", "table")
}

func (gn *GlobalNotes) GetTopLevelFormatted() string {
	return gn.QueryToHtml("select title, created, Author from notes where parent is null GROUP BY type ORDER BY created ", "table")
}

func (gn *GlobalNotes) GetLogsFormated() string {
	return gn.QueryToHtml("select title, start_time, end_time, end_time - start_time from notes where type = 'log' ORDER BY created desc", "table")
}

func (gn *GlobalNotes) BlockToHtml3(b pmd.SyntaxNode) string {
	res := gn.BlockToHtml(b)
	re := regexp.MustCompile(`@([a-f0-9-]+)`)
	res = re.ReplaceAllStringFunc(res, func(s string) string {
		nid := re.FindStringSubmatch(s)[1]
		note_id, err := gn.GetIdByPartial(PartialNoteId(nid))
		if err != nil {
			return s
		}
		note := gn.GetNoteByID(note_id)
		return fmt.Sprintf("<a href=\"%s.html\">%s %s</a>", nid, note.GetIconHtml(), note.Title)
	})

	plugin := regexp.MustCompile(`@{([a-z.]+):([^}]*)}`)
	p := Plugin{}
	res = plugin.ReplaceAllStringFunc(res, func(s string) string {
		plug := plugin.FindStringSubmatch(s)[1]
		args := plugin.FindStringSubmatch(s)[2]
		return p.Render(plug, args)
	})

	return res
}
