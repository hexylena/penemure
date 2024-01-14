package models

import (
	"encoding/json"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"text/template"
	"time"

	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	"github.com/google/uuid"
	"gopkg.in/yaml.v3"
	// "github.com/gomarkdown/markdown"
	// "github.com/gomarkdown/markdown/ast"
	// "github.com/gomarkdown/markdown/html"
	// "github.com/gomarkdown/markdown/parser"
)

// const (
// 	Project Season = iota
// 	Task
// 	Note
// 	Time
// )

type NoteId string

type PartialNoteId string

type SimpleMeta map[string]any

type Meta struct {
	Type  string `json:"type"`
	Title string `json:"title"`
	Value any    `json:"value"`
	Icon  string `json:"icon"`
}

func (m *Meta) GetIconHtml() string {
	if m.Title == "Status" {
		return "🚦"
	} else if m.Title == "Assignee" {
		return "👤"
	} else if m.Title == "Tags" {
		return "🏷"
	} else if m.Title == "Due" {
		return "📅"
	} else if m.Title == "Estimate" {
		return "⏱"
	} else if m.Title == "Priority" {
		return "🔥"
	} else if m.Title == "Effort" {
		return "🏋️"
	} else if m.Title == "Progress" {
		return "📈"
	} else if m.Title == "Start" {
		return "🏁"
	} else if m.Title == "End" {
		return "🏁"
	} else if m.Title == "Created" {
		return "📅"
	} else if m.Title == "Modified" {
		return "📅"
	} else if m.Title == "Completed" {
		return "📅"
	} else if m.Title == "Blocked" {
		return "🚫"
	} else if m.Title == "Blocking" {
		return "🚫"
	}

	if len(m.Icon) <= 10 {
		return m.Icon
	}
	// Remote icons
	if m.Icon[:4] == "http" {
		return fmt.Sprintf("<img src=\"%s\" />", m.Icon)
	}
	// Local icons
	return fmt.Sprintf("<img src=\"file://%s\" />", m.Icon)
}

func (m *Meta) String() string {
	return fmt.Sprintf("%s=%s", m.Title, m.Value)
}

type Note struct {
	NoteId NoteId `yaml:"id" json:"id"`
	Title  string `json:"title"`
	Type   string `json:"type"`

	Projects []NoteId `json:"projects"`
	Parents  []NoteId `json:"parents"`
	Blocking []NoteId `json:"blocking"`

	Blocks     []*Block `json:"_blocks" yaml:"contents"`
	Meta       []*Meta  `json:"_tags" yaml:"tags"`
	CreatedAt  int      `json:"created"`
	ModifiedAt int      `json:"modified"`
	modified   bool
}

// Parse a note from projects/7/1/7177e07a-7701-42a5-ae4f-c2c5bc75a974.json
func (n *Note) ParseNote(path string) {
	// Read the file
	jsonFile, err := os.Open(path)
	if err != nil {
		fmt.Println(err)
	}
	defer jsonFile.Close()

	// read our opened jsonFile as a byte array.
	byteValue, err := ioutil.ReadAll(jsonFile)
	if err != nil {
		fmt.Println(err)
	}

	// parse the byte array
	json.Unmarshal(byteValue, &n)
}

func (n *Note) Touch() {
	n.ModifiedAt = int(time.Now().Unix())
	n.modified = true
}

func NewNote() *Note {
	n := &Note{
		CreatedAt:  int(time.Now().Unix()),
		ModifiedAt: int(time.Now().Unix()),
		NoteId:     NoteId(uuid.New().String()),
	}
	return n
}

func (n *Note) IsModified() bool {
	return n.modified
}

func (n *Note) HasParents() bool {
	return len(n.Parents) > 0
}

func (n *Note) HasBlocks() bool {
	return len(n.Blocks) > 0
}

func (n *Note) GetIconHtml() string {
	var icon string

	for _, tag := range n.Meta {
		if tag.Type == "icon" {
			icon = tag.Icon
		}
	}

	if icon == "" {
		if n.Type == "project" {
			return "📁"
		}
		if n.Type == "task" {
			return "📌"
		}
		if n.Type == "note" {
			return "🗒"
		}
	}

	// Remote icons
	if icon[:4] == "http" {
		return fmt.Sprintf("<img src=\"%s\" />", icon)
	}
	// Local icons
	// if it has a / and a .
	if regexp.MustCompile(`\/.*\.`).MatchString(icon) {
		return fmt.Sprintf("<img src=\"file://%s\" />", icon)
	}
	return icon
}

func (n *Note) Export(gn *GlobalNotes) {
	// Save contents to ./export/<id>.html
	// Read template from templates/note.html
	tmpl_text, err := os.ReadFile("templates/note.html")
	if err != nil {
		fmt.Println(err)
	}
	tmpl, err := template.New("note").Parse(string(tmpl_text))
	if err != nil {
		fmt.Println(err)
	}

	// Render template
	// Save to ./export/<id>.html
	f, err := os.Create(fmt.Sprintf("export/%s.html", n.NoteId))
	if err != nil {
		fmt.Println(err)
	}

	type tmpstruct struct {
		Note        *Note
		GlobalNotes *GlobalNotes
	}

	err = tmpl.Execute(f, tmpstruct{n, gn})
	if err != nil {
		fmt.Println(err)
	}
}

// Save note
func (n *Note) SaveNote(path string) {
	// Serialize the note
	jsonNote, err := json.Marshal(n)
	if err != nil {
		fmt.Println(err)
	}
	// dirname
	dir := filepath.Dir(path)
	// Create the directory if it doesn't exist
	if _, err := os.Stat(dir); os.IsNotExist(err) {
		os.MkdirAll(dir, os.ModePerm)
	}

	// Write the file
	err = ioutil.WriteFile(path, jsonNote, 0644)
	if err != nil {
		fmt.Println(err)
	}
}

func (n *Note) Id() string {
	// TODO: dynamic on db size?
	return fmt.Sprint(n.NoteId)[:8]
}

func (n *Note) GetMetaKey(key string) (*Meta, error) {
	for _, tag := range n.Meta {
		if tag.Title == key {
			return tag, nil
		}
	}
	return nil, errors.New("no such tag")
}

func (n *Note) GetS(key string) string {
	for _, tag := range n.Meta {
		if tag.Title == key {
			// switch tag.Value.(type) {
			// case string:
			// 	return tag.Value.(string)
			// case []string:
			// 	return fmt.Sprintf("%v", tag.Value)
			// default:
			// 	return fmt.Sprintf("%v", tag.Value)
			// }
			return fmt.Sprintf("%v", tag.Value)
		}
	}
	return ""
}

func (n *Note) GetMeta() [][]string {
	rows := [][]string{}
	for _, tag := range n.Meta {
		rows = append(rows, []string{tag.Title, fmt.Sprintf("%v", tag.Value)})
	}
	return rows
}

func (n *Note) BubblePrint() {
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

	var h1 = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FAFAFA")).
		Background(lipgloss.Color("#7D56F4")).
		Width(32)

	var h2 = lipgloss.NewStyle().
		Bold(true).
		Foreground(lipgloss.Color("#FAFAFA")).
		Background(lipgloss.Color("#9D76F4")).
		Width(32)

	fmt.Println(h1.Render(n.Title))
	fmt.Println("\n")
	fmt.Println(h2.Render("Meta"))

	rows := n.GetMeta()

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
		Headers("Key", "Value").
		Rows(rows...)

	fmt.Println(t)

	fmt.Println("\n")
	fmt.Println(h2.Render("Contents"))

	md := n.RenderMarkdown()

	out, err := glamour.Render(md, "auto")
	if err != nil {
		panic(err)
	}
	fmt.Print(out)

}

func (n *Note) RenderMarkdown() string {
	out := ""
	for _, block := range n.Blocks {
		switch block.Type {
		case H1:
			out += "# " + block.Contents + "\n\n"
		case H2:
			out += "## " + block.Contents + "\n\n"
		case H3:
			out += "### " + block.Contents + "\n\n"
		case P:
			out += block.Contents + "\n\n"
		}
	}
	return out
}

func (n *Note) SerialiseToFrontmatterMarkdown() string {
	// Write out the note to a temp file
	tmpfile, err := ioutil.TempFile("", "note")
	if err != nil {
		panic(err)
	}
	defer tmpfile.Close()

	// tmpfile.Write([]byte("---\n"))
	bb, _ := yaml.Marshal(n)
	tmpfile.Write([]byte(bb))
	// tmpfile.Write([]byte("---\n\n"))
	// tmpfile.Write([]byte(n.RenderMarkdown()))
	return tmpfile.Name()
}

func (n *Note) ParseNoteFromMarkdown(path string) Note {
	// Read in path
	file, err := os.Open(path)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	//parse the file as yaml
	bytes, err := ioutil.ReadAll(file)
	var n2 Note
	yaml.Unmarshal(bytes, &n2)
	n2.Touch()

	// Remove the path
	os.Remove(path)
	return n2
}

func (n *Note) Edit() Note {
	path := n.SerialiseToFrontmatterMarkdown()

	// Open the editor
	editor := os.Getenv("EDITOR")
	if editor == "" {
		editor = "vim"
	}
	cmd := exec.Command(editor, "+4", path)
	cmd.Stdin = os.Stdin
	cmd.Stdout = os.Stdout
	cmd.Stderr = os.Stderr
	cmd.Run()

	return n.ParseNoteFromMarkdown(path)
}

func (n *Note) GetProjectMembers(gn GlobalNotes) []Note {
	out := make([]Note, 0)
	if n.Type != "project" {
		return out
	}

	// Every single note
	for _, note := range gn.GetNotes() {
		// Check their projects
		for _, project := range note.Projects {
			// If their project list includes 'this' note
			if project == n.NoteId {
				out = append(out, *note)
			}
		}
	}

	return out
}
