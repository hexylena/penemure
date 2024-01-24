package cmd

import (
	"fmt"
	pma "github.com/hexylena/pm/adapter"
	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

type (
	errMsg error
)

const (
	hotPink  = lipgloss.Color("#FF06B7")
	darkGray = lipgloss.Color("#767676")
)

var (
	inputStyle    = lipgloss.NewStyle().Foreground(hotPink)
	continueStyle = lipgloss.NewStyle().Foreground(darkGray)

	focusedStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("205"))
	blurredStyle = lipgloss.NewStyle().Foreground(lipgloss.Color("240"))

	focusedButtonStart = focusedStyle.Copy().Render("[ Start ]")
	blurredButtonStart = fmt.Sprintf("[ %s ]", blurredStyle.Render("Start"))
	focusedButtonStop  = focusedStyle.Copy().Render("[ Stop ]")
	blurredButtonStop  = fmt.Sprintf("[ %s ]", blurredStyle.Render("Stop"))
)

type model struct {
	newInput     []textinput.Model
	newStartTime int64
	oldData      [][]textinput.Model
	focusedRow   int
	focusedCol   int
	err          error
	running      bool
}

const (
	title = iota
	tags
	project
	start
	end
	// button_go
	// button_edit
)

func generateNewInput() []textinput.Model {
	var newInput []textinput.Model = make([]textinput.Model, 5)

	newInput[title] = textinput.New()
	newInput[title].Placeholder = "Meeting with Alice"
	newInput[title].Focus()
	newInput[title].Width = 30

	newInput[tags] = textinput.New()
	newInput[tags].Placeholder = "#meeting"
	newInput[tags].Width = 15

	newInput[project] = textinput.New()
	newInput[project].Placeholder = "Project"
	newInput[project].Width = 15

	newInput[start] = textinput.New()
	newInput[start].Placeholder = "--:--"
	newInput[start].Width = 6

	newInput[end] = textinput.New()
	newInput[end].Placeholder = "--:--"
	newInput[end].Width = 6

	return newInput
}

func initialiseNewInput(m *model) {
	newInput := generateNewInput()
	m.newInput = newInput
	m.newStartTime = 0
}

func initialModel() model {
	m := model{
		focusedRow: 0,
		focusedCol: 0,
		err:        nil,
		running:    false,
	}
	initialiseNewInput(&m)

	m.oldData = make([][]textinput.Model, 0)
	m.oldData = append(m.oldData, generateNewInput())
	// todo: initalise old inputs

	return m
}

func (m model) Init() tea.Cmd {
	return textinput.Blink
}

func (m model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	var cmds []tea.Cmd = make([]tea.Cmd, len(m.newInput))

	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.Type {
		case tea.KeyCtrlC, tea.KeyEsc:
			return m, tea.Quit
		case tea.KeyShiftTab, tea.KeyCtrlP:
			m.prevInput()
		case tea.KeyTab, tea.KeyCtrlN:
			m.nextInput()
		case tea.KeyEnter:
			if m.focusedRow == 1 {
				if !m.running {
					// Set start time to current integer time
					m.newStartTime = time.Now().Unix()
					m.running = true
				} else {
					m.running = false
					// save entry
					note := pmm.NewNote()
					note.Title = m.newInput[title].Value()
					note.Type = "log"
					tags := strings.Split(m.newInput[tags].Value(), " ")
					for _, tag := range tags {
						note.AddTag(tag)
					}
					note.AddMeta("time", "start_time", strconv.FormatInt(m.newStartTime, 10))
					note.AddMeta("time", "end_time", strconv.FormatInt(time.Now().Unix(), 10))

					// Must be registered in the adapter or it gets lost
					gn.RegisterNote(note)
					// Must persist
					pma.SaveNotes(gn)

					m.oldData = append(m.oldData, m.newInput)
					// clear inputs
					initialiseNewInput(&m)
				}
			}
		}

		for col := range m.newInput {
			m.newInput[col].Blur()
		}

		for row := range m.oldData {
			for col := range m.oldData[row] {
				m.oldData[row][col].Blur()
			}
		}

		if m.focusedRow == 0 {
			m.newInput[m.focusedCol].Focus()
		}

	// We handle errors just like any other message
	case errMsg:
		m.err = msg
		return m, nil
	}

	// for row := range m.inputs {
	for col := range m.newInput {
		m.newInput[col], cmds[col] = m.newInput[col].Update(msg)
	}
	// }
	return m, tea.Batch(cmds...)
}

func (m model) View() string {
	out := ""

	// for row := range m.inputs {
	out += fmt.Sprintf(
		`%s %s %s %s %s`,
		inputStyle.Width(30+3).Render("Title"),
		inputStyle.Width(15+3).Render("Tags"),
		inputStyle.Width(15+3).Render("Project"),
		inputStyle.Width(15+3).Render("Start"),
		// inputStyle.Width(15 + 3).Render("End"),
	) + "\n"

	clockTime := "--:--"
	if m.newStartTime != 0 {
		clockTime = time.Unix(m.newStartTime, 0).Format("15:04")
	}
	out += fmt.Sprintf(
		`%s %s %s %s`,
		m.newInput[title].View(),
		m.newInput[tags].View(),
		m.newInput[project].View(),
		clockTime,
		// m.inputs[row][start].View(),
		// m.inputs[row][end].View(),
	) + "\n"
	// }

	button := &blurredButtonStart
	if !m.running {
		button = &blurredButtonStart
		if m.focusedRow == 1 {
			button = &focusedButtonStart
		}
	} else {
		button = &blurredButtonStop
		if m.focusedRow == 1 {
			button = &focusedButtonStop
		}
	}
	out += fmt.Sprintf("\n\n%s\n\n", *button)

	for row := range m.oldData {
		out += fmt.Sprintf(
			`%s %s %s %s %s`,
			m.oldData[row][title].View(),
			m.oldData[row][tags].View(),
			m.oldData[row][project].View(),
			m.oldData[row][start].View(),
			m.oldData[row][end].View(),
		) + "\n"
	}

	return out
}

// nextInput focuses the next input field
func (m *model) nextInput() {
	if m.focusedRow == 0 {
		if m.focusedCol+1 == 3 {
			m.focusedCol = 0
			m.focusedRow++
		} else {
			m.focusedCol++
		}
	} else {
		// wrap around
		m.focusedCol = 0
		m.focusedRow = 0
	}
}

// prevInput focuses the previous input field
func (m *model) prevInput() {
	if m.focusedRow == 0 {
		if m.focusedCol == 0 {
			// pass
		} else {
			m.focusedCol--
		}
	} else {
		m.focusedRow--
		m.focusedCol = 2
	}
}

func init() {
	rootCmd.AddCommand(timeCmd)
}

var timeCmd = &cobra.Command{
	Use:   "time [note id]",
	Short: "time a note",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		p := tea.NewProgram(initialModel(), tea.WithAltScreen())
		if _, err := p.Run(); err != nil {
			log.Fatal(err)
		}
	},
}

//
// Add new
// [textbox] [tags] [project] [start time] [end time] ▶️
//
// 2024-01-02
// meeting with jane   #work #meeting  BY-COVID  12:00    14:32  ▶️
// meeting with alice  #work #meeting  GTN       11:00    12:00  ▶️
//
// 2024-01-01
// meeting with bob    #work #meeting  GTN       10:00    11:00  ▶️
//
// Notes:
// all times should be editable if you tab into it.
// jk to move up/down, hl to move between fields (+arrow keys), tab also.
// type to overwrite, moving fields saves.
//
// Data Model:
// this is a "log" (time / notes / times+notes)
// that is (generally) attached to a Note/Task, and associated with a Project.
