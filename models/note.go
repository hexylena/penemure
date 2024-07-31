package models

import (
	"bufio"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"io/ioutil"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
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

	pmd "github.com/hexylena/pm/md"
)

// const (
// 	Project Season = iota
// 	Task
// 	Note
// 	Time
// )

type NoteId string

func (n *NoteId) String() string {
	return string(*n)
}

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
	} else if m.Type == "time" {
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
	} else if m.Icon == "" {
		return ""
	}

	// Remote icons
	if m.Icon[:4] == "http" {
		return fmt.Sprintf("<img src=\"%s\" />", m.Icon)
	} else if LooksLocal(m.Icon) {
		return fmt.Sprintf("<img src=\"file://%s\" />", m.Icon)
	}
	return m.Icon
}

func (m *Meta) String() string {
	return fmt.Sprintf("%s=%s", m.Title, m.Value)
}

func (m *Meta) AutoFmt() string {
	value := fmt.Sprintf("%v", m.Value)
	// if it looks like a url, make it a link
	if strings.Contains(value, "http") {
		return "<a href=\"" + value + "\">" + value + "</a>"
	}

	if m.Type == "tag" {
		return fmt.Sprintf("<a href=\"search.html?title=%s\">%s</a>", strings.Trim(value, "#"), value)
	}

	uuid_regex := regexp.MustCompile(`^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$`)
	// uuid_short := regexp.MustCompile(`^[a-f0-9]{8}$`)

	// if it looks like a uuid, by regex, make it a link
	if uuid_regex.MatchString(value) {
		return "<a href=\"" + value + ".html\">" + value + "</a>"
	}
	// if uuid_short.MatchString(value) {
	// 	full_value := fmt.Sprint(gn.GetIdByPartial(PartialNoteId(value)))
	// 	return "<a href=\"" + full_value + ".html\">" + value + "</a>"
	// }

	if m.Title == "created" || m.Title == "modified" || m.Title == "start_time" || m.Title == "end_time" {
		// parse unix time
		i, err := strconv.ParseInt(value, 10, 64)
		if err != nil {
			panic(err)
		}
		t := time.Unix(i, 0)

		return t.Format("2006-01-02 15:04:05")
	}

	return value
}

type Note struct {
	NoteId NoteId `yaml:"id" json:"id"`
	Title  string `json:"title"`
	Type   string `json:"type"`

	Parents  []NoteId `json:"parents"`
	Blocking []NoteId `json:"blocking"`

	Blocks     []pmd.SyntaxNode `json:"_blocks" yaml:"-"`
	Meta       []*Meta          `json:"_tags" yaml:"tags"`
	CreatedAt  int              `json:"created"`
	ModifiedAt int              `json:"modified"`
	modified   bool

	Version int `json:"version"`
}

func (n *Note) String() string {
	return fmt.Sprintf("%s (%s)", n.Title, n.Id())
}

func (ce *Note) UnmarshalJSON(b []byte) error {
	// First, deserialize everything into a map of map
	var objMap map[string]*json.RawMessage
	err := json.Unmarshal(b, &objMap)
	if err != nil {
		return err
	}

	// Must manually deserialise each item
	if objMap["id"] != nil {
		err = json.Unmarshal(*objMap["id"], &ce.NoteId)
		if err != nil {
			return err
		}
	}

	if objMap["title"] != nil {
		err = json.Unmarshal(*objMap["title"], &ce.Title)
		if err != nil {
			return err
		}
	}

	if objMap["type"] != nil {
		err = json.Unmarshal(*objMap["type"], &ce.Type)
		if err != nil {
			return err
		}
	}

	if objMap["version"] != nil {
		err = json.Unmarshal(*objMap["version"], &ce.Version)
		if err != nil {
			return err
		}
	}

	if objMap["parents"] != nil {
		err = json.Unmarshal(*objMap["parents"], &ce.Parents)
		if err != nil {
			return err
		}
	}

	if objMap["blocking"] != nil {
		err = json.Unmarshal(*objMap["blocking"], &ce.Blocking)
		if err != nil {
			return err
		}
	}

	if objMap["created"] != nil {
		err = json.Unmarshal(*objMap["created"], &ce.CreatedAt)
		if err != nil {
			return err
		}
	}

	if objMap["modified"] != nil {
		err = json.Unmarshal(*objMap["modified"], &ce.ModifiedAt)
		if err != nil {
			return err
		}
	}

	if objMap["_tags"] != nil {
		err = json.Unmarshal(*objMap["_tags"], &ce.Meta)
		if err != nil {
			return err
		}
	}

	if objMap["_blocks"] != nil {
		var rawMessagesBlocks []*json.RawMessage
		err = json.Unmarshal(*objMap["_blocks"], &rawMessagesBlocks)
		if err != nil {
			logger.Error("error unmarshalling _blocks", "error", err)
			return err
		}

		// Let's add a place to store our de-serialized Plant and Animal structs
		ce.Blocks = make([]pmd.SyntaxNode, len(rawMessagesBlocks))

		var m map[string]interface{}
		for index, rawMessage := range rawMessagesBlocks {
			err = json.Unmarshal(*rawMessage, &m)
			if err != nil {
				return err
			}

			// Depending on the type, we can run json.Unmarshal again on the same byte slice
			// But this time, we'll pass in the appropriate struct instead of a map
			if m["type"] == "heading" {
				var p pmd.Heading
				err := json.Unmarshal(*rawMessage, &p)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &p
			} else if m["type"] == "paragraph" {
				var a pmd.Paragraph
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				// After creating our struct, we should save it
				ce.Blocks[index] = &a
			} else if m["type"] == "image" {
				var a pmd.Image
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "list" {
				var a pmd.List
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "horizontal_rule" {
				var a pmd.HorizontalRule
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "table_view" {
				var a pmd.TableView
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "code" {
				var a pmd.Code
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else if m["type"] == "link" {
				var a pmd.Link
				err := json.Unmarshal(*rawMessage, &a)
				if err != nil {
					return err
				}
				ce.Blocks[index] = &a
			} else {
				return errors.New(fmt.Sprintf("Unknown type: %s", m["type"]))
			}
		}
	}

	// That's it!  We made it the whole way with no errors, so we can return `nil`
	return nil
}

// Parse a note from projects/7/1/7177e07a-7701-42a5-ae4f-c2c5bc75a974.json
func (n *Note) ParseNote(path string) {
	// Read the file
	jsonFile, err := os.Open(path)
	if err != nil {
		logger.Error("error loading file ", "error", err, "path", path)
	}
	defer jsonFile.Close()

	// read our opened jsonFile as a byte array.
	byteValue, err := ioutil.ReadAll(jsonFile)
	if err != nil {
		fmt.Println(err)
	}

	// fmt.Println(byteValue)
	fmt.Println(GetVersion(byteValue))
	Migrate(byteValue, n)
}

func (n *Note) Touch() {
	n.ModifiedAt = int(time.Now().Unix())
	n.modified = true
}

func (n *Note) AddTag(t string) {
	n.Touch()
	if len(n.GetL("Tags")) == 0 {
		n.Meta = append(n.Meta, &Meta{
			Type:  "tag",
			Title: "Tags",
			Value: t,
		})
	}
}

func (n *Note) AddMetaTag(k string, v string) {
	n.Touch()
	n.Meta = append(n.Meta, &Meta{
		Type:  "tag",
		Title: k,
		Value: v,
	})
}

func (n *Note) AddMeta(typ string, k string, v string) {
	n.Touch()
	n.Meta = append(n.Meta, &Meta{
		Type:  typ,
		Title: k,
		Value: v,
	})
}

func NewNote() *Note {
	n := &Note{
		CreatedAt:  int(time.Now().Unix()),
		ModifiedAt: int(time.Now().Unix()),
		NoteId:     NoteId(uuid.New().String()),
		modified:   true,
	}
	return n
}

func (n *Note) IsModified() bool {
	return n.modified
}

func (n *Note) Projects() []*Note {
	return []*Note{}
}

func (n *Note) HasParents() bool {
	return len(n.Parents) > 0
}

func (n *Note) HasParent(o NoteId) bool {
	for _, p := range n.Parents {
		if p == o {
			return true
		}
	}
	return false
}

func (n *Note) AddParent(o NoteId) {
	n.Parents = append(n.Parents, o)
	n.Touch()
}

func (n *Note) SetParent(o NoteId) {
	n.Parents = []NoteId{o}
	n.Touch()
}

func (n *Note) HasBlocks() bool {
	return len(n.Blocks) > 0
}

func (n *Note) GetEmoji() string {
	if n.Type == "project" {
		return "📁"
	} else if n.Type == "task" {
		if n.GetS("Status") == "done" || n.GetS("Status") == "completed"{
			return "✅"
		} else if n.GetS("Status") == "in progress" {
			return "🚧"
		} else if n.GetS("Status") == "blocked" {
			return "🚫"
		} else {
			return "📝"
		}
	} else if n.Type == "person" {
		return "👩‍🦰"
	} else if n.Type == "note" {
		return "🗒"
	} else if n.Type == "log" {
		return "⏰"
	} else {
		return "?"
	}
}

func (n *Note) GetIconHtml() string {
	var icon string

	for _, tag := range n.Meta {
		if tag.Type == "icon" {
			icon = tag.Icon
		}
	}

	if icon == "" {
		return n.GetEmoji()
	}

	// Remote icons
	if icon[:4] == "http" {
		return fmt.Sprintf("<img src=\"%s\" />", icon)
	}
	// Local icons
	// if it has a / and a .
	if LooksLocal(icon) {
		return fmt.Sprintf("<img src=\"file://%s\" />", icon)
	}
	return icon
}

func (n *Note) GetCover() string {
	for _, tag := range n.Meta {
		if tag.Type == "cover" {
			return tag.Value.(string)
		}
	}
	return ""
}

func LooksLocal(path string) bool {
	return regexp.MustCompile(`^\.\/`).MatchString(path)
}

func (n *Note) ExportToFile(gn *GlobalNotes) {
	// Save contents to ./export/<id>.html

	// Save to ./export/<id>.html
	f, err := os.Create(fmt.Sprintf("export/%s.html", n.NoteId))
	logger.Info("Exporting", "note", n.String(), "file", f.Name())
	if err != nil {
		fmt.Println(err)
	}
	n.Export(gn, bufio.NewWriter(f))
	f.Close()
}

func (n *Note) Export(gn *GlobalNotes, w io.Writer) {
	tmpl, err := template.New("").ParseFiles("templates/note.html", "templates/base.html")
	if err != nil {
		logger.Error("Error", "err", err)
	}

	type tmpstruct struct {
		Note        *Note
		GlobalNotes *GlobalNotes
	}

	err = tmpl.ExecuteTemplate(w, "base", tmpstruct{n, gn})
	if err != nil {
		logger.Error("error executing template", "error", err)
	}
	// TODO: copy icon, cover if local
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

func (n *Note) GetL(key string) []string {
	for _, tag := range n.Meta {
		if tag.Title == key {
			switch tag.Value.(type) {
			case []string:
				return tag.Value.([]string)
			default:
				return []string{fmt.Sprintf("%v", tag.Value)}
			}
		}
	}
	return []string{}
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
	fmt.Print("\n\n")
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

	fmt.Print("\n\n")
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
		out += block.Md() + "\n\n"
	}
	return out
}

func (n *Note) RenderFrontmatterMarkdown() string {
	out := "---\n"
	bb, _ := yaml.Marshal(n)
	out += string(bb)
	out += "---\n"
	for _, block := range n.Blocks {
		fmt.Println(block)
		out += block.Md() + "\n\n"
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

	tmpfile.Write([]byte("---\n"))
	bb, _ := yaml.Marshal(n)
	tmpfile.Write([]byte(bb))
	tmpfile.Write([]byte("---\n\n"))
	tmpfile.Write([]byte(n.RenderMarkdown()))
	return tmpfile.Name()
}

func (n *Note) ParseNoteFromMarkdown(path string) Note {
	// Read in path
	file, err := os.Open(path)
	if err != nil {
		panic(err)
	}
	defer file.Close()

	// Read in entire file
	scanner := bufio.NewScanner(file)
	contents := make([]string, 0)

	fronmatter_markers := make([]int, 0)

	for scanner.Scan() {
		line := scanner.Text()
		if line == "---" {
			fronmatter_markers = append(fronmatter_markers, len(contents))
		}
		contents = append(contents, line)
	}

	// slice out the frontmatter portion
	frontmatter := contents[fronmatter_markers[0]+1 : fronmatter_markers[1]]

	// Read in the rest of the markdown
	markdown := contents[fronmatter_markers[1]+1:]

	// Unmarshal frontmatter
	var n2 Note
	err = yaml.Unmarshal([]byte(strings.Join(frontmatter, "\n")), &n2)
	if err != nil {
		panic(err)
	}

	// Parse markdown
	// fmt.Println("Parsing markdown", markdown)
	n2.Blocks = pmd.MdToBlocks([]byte(strings.Join(markdown, "\n")))
	// fmt.Println("Parsed markdown", n2.Blocks)
	// for _, block := range n2.Blocks {
	// 	fmt.Println("Block", block.Html())
	// }

	n2.Touch()

	// Remove the path
	os.Remove(path)

	// return *n
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

	// Every single note
	for _, note := range gn.GetNotes() {
		// Check their projects
		for _, project := range note.Parents {
			// If their project list includes 'this' note
			if project == n.NoteId {
				out = append(out, *note)
			}
		}
	}

	return out
}

func (n *Note) GetStartEndTime(t string) (time.Time, error) {
	time_key := fmt.Sprintf("%s_time", t)
	unix_time_string := n.GetS(time_key)
	if unix_time_string == "" {
		return time.Time{}, errors.New(fmt.Sprintf("No %s time", t))
	}

	unix_time, err := strconv.ParseInt(unix_time_string, 10, 64)
	if err != nil {
		return time.Time{}, err
	}

	return time.Unix(unix_time, 0), nil
}

type FlatNote map[string]string

func (n *Note) Flatten() FlatNote {
	out := FlatNote{
		// Custom
		"short_id": n.Id(),
		"icon": n.GetEmoji(),

		// Built In
		"id":       fmt.Sprint(n.NoteId),
		"title":    n.Title,
		"type":     n.Type,
		"created":  fmt.Sprint(n.CreatedAt),
		"modified": fmt.Sprint(n.ModifiedAt),
		// Separate with unicode Record Separator
		"parent":   strings.Join(StringifyNoteIds(n.Parents), "\u001E"),
		"blocking": strings.Join(StringifyNoteIds(n.Blocking), "\u001E"),
	}
	for _, tag := range n.Meta {
		if tag.Title != "" {
			out[tag.Title] = fmt.Sprintf("%v", tag.Value)
		} else {
			out[tag.Type] = fmt.Sprintf("%v", tag.Value)
		}
	}
	return out
}

func StringifyNoteIds(nid []NoteId) []string {
	out := make([]string, len(nid))
	for i, id := range nid {
		out[i] = fmt.Sprint(id)
	}
	return out
}
