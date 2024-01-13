package models

import (
	// "bufio"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	// "strings"
	"github.com/charmbracelet/glamour"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	"gopkg.in/yaml.v3"
	"os/exec"
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

type BlockType string

const (
	H1 BlockType = "h1"
	H2 BlockType = "h2"
	H3 BlockType = "h3"
	P  BlockType = "p"
)

type NoteId string

type Block struct {
	Contents string    `json:"contents"`
	Type     BlockType `json:"type"`
}

type SimpleMeta map[string]any

type Meta struct {
	Type  string `json:"type"`
	Title string `json:"title"`
	Value any    `json:"value"`
	Icon  string `json:"icon"`
}

type Note struct {
	Created  int      `json:"created"`
	NoteId   string   `yaml:"id" json:"id"`
	Title    string   `json:"title"`
	Type     string   `json:"type"`
	Parents  []NoteId `json:"parents"`
	Blocks   []Block  `json:"_blocks" yaml:"blocks"`
	Meta     []Meta   `json:"_tags" yaml:"tags"`
	modified bool
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

func (n *Note) IsModified() bool {
	return n.modified
}

// Save note
func (n *Note) SaveNote(path string) {
	// Serialize the note
	jsonNote, err := json.Marshal(n)
	if err != nil {
		fmt.Println(err)
	}

	err = ioutil.WriteFile(path, jsonNote, 0644)
}

func (n *Note) Id() string {
	// TODO: dynamic on db size?
	return n.NoteId[:8]
}

func (n *Note) GetS(key string) string {
	for _, tag := range n.Meta {
		if tag.Title == key {
			switch tag.Value.(type) {
			case string:
				return tag.Value.(string)
			case []string:
				return fmt.Sprintf("%v", tag.Value)
			}
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

	tmpfile.Write([]byte("---\n"))
	bb, _ := yaml.Marshal(n)
	tmpfile.Write([]byte(bb))
	tmpfile.Write([]byte("---\n\n"))
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
	n2.modified = true

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
