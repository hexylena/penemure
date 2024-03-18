package cmd

import (
	"fmt"
	pma "github.com/hexylena/pm/adapter"
	// "os"
	pmm "github.com/hexylena/pm/models"
	"github.com/spf13/cobra"
	"log"
	"sort"
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
	note  *pmm.Note
}

const (
	title = iota
	tags
	project
	start
	end
	internal_id
	// button_go
	// button_edit
)

func generateNewInput(n *pmm.Note, m *model) []textinput.Model {
	var newInput []textinput.Model = make([]textinput.Model, 6)

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

	if n != nil {
		newInput[title].SetValue(n.Title)
		// newInput[tags] = n.Meta //TODO
		// newInput[project] = n.Project // TODO
		newInput[start].SetValue(fmt.Sprintf("%d", m.newStartTime))
	}

	return newInput
}

func initialiseNewInput(m *model) {
	// Check if there's an open interval, and if so, use it.
	first_open_interval := gn.GetOpenLog()
	if first_open_interval != nil {
		m.note = first_open_interval

		start_time, err := m.note.GetStartEndTime("start")
		if err != nil {
			panic(err)
		}

		m.running = true
		m.newStartTime = start_time.Unix()
	} else {
		m.newStartTime = 0
	}



	newInput := generateNewInput(m.note, m)
	m.newInput = newInput

}

func obtainOldData(m *model) {
	m.oldData = make([][]textinput.Model, 0)
	times := gn.GetLogs(false, true)

	grouped_items := make(map[string][]*pmm.Note)
	for _, t := range times {
		start, _ := t.GetStartEndTime("start")
		// end, _ := t.GetStartEndTime("end")

		day := start.Format("2006-01-02")
		grouped_items[day] = append(grouped_items[day], t)
	}

	day_keys := make([]string, 0)
	for k := range grouped_items {
		day_keys = append(day_keys, k)
	}

	// Reverse Sort the days
	sort.Slice(day_keys, func(i, j int) bool {
		return day_keys[i] > day_keys[j]
	})

	for _, day := range day_keys {
		items := grouped_items[day]

		for _, t := range items {
			newInput := generateNewInput(nil, nil)
			newInput[title].SetValue(t.Title)
			newInput[tags].SetValue(t.GetS("tags"))

			t1, _ := t.GetStartEndTime("start")
			t2, _ := t.GetStartEndTime("end")

			hh_mm1 := t1.Format("15:04")
			hh_mm2 := t2.Format("15:04")

			newInput[start].SetValue(hh_mm1)
			newInput[end].SetValue(hh_mm2)

			newInput[internal_id].SetValue(fmt.Sprint(t.NoteId))

			// Clear placeholders
			newInput[title].Placeholder = ""
			newInput[tags].Placeholder = ""
			newInput[project].Placeholder = ""
			newInput[start].Placeholder = ""

			m.oldData = append(m.oldData, newInput)
		}
	}

	// for _, t := range times {
	// 	// projects := gn.GetProjectsForNote(t)
	// 	newInput := generateNewInput()
	// 	newInput[title].SetValue(t.Title)
	// 	newInput[tags].SetValue(t.GetS("tags"))
	// 	// newInput[project].SetValue(t.Projects[0])
	// 	// newInput[start].SetValue(t.GetS("start_time"))
	// 	// newInput[end].SetValue(t.GetS("end_time"))
	// 	m.oldData = append(m.oldData, newInput)
	// }
}

func initialModel() model {
	m := model{
		focusedRow: 0,
		focusedCol: 0,
		err:        nil,
		running:    false,
	}

	initialiseNewInput(&m)

	obtainOldData(&m)
	// m.oldData = append(m.oldData, generateNewInput())
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
			// If we press enter
			// Specifically on the start button, trigger this.
			if m.focusedRow == 1 {
				if !m.running {
					// Set start time to current integer time
					m.newStartTime = time.Now().Unix()
					m.running = true

					m.note = pmm.NewNote()
					m.note.Title = m.newInput[title].Value()
					m.note.Type = "log"
					tags := strings.Split(m.newInput[tags].Value(), " ")
					for _, tag := range tags {
						m.note.AddTag(tag)
					}
					m.note.AddMeta("time", "start_time", strconv.FormatInt(m.newStartTime, 10))
					// Must be registered in the adapter or it gets lost
					gn.RegisterNote(m.note)
					// Must persist
					pma.SaveNotes(gn)
				} else {
					m.running = false
					// save entry
					m.note.AddMeta("time", "end_time", strconv.FormatInt(time.Now().Unix(), 10))

					// might duplicately register but that shouldn't be an issue.
					gn.RegisterNote(m.note)

					// Must persist
					pma.SaveNotes(gn)

					m.oldData = append(m.oldData, m.newInput)
					m.newStartTime = 0
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
	out := fmt.Sprintf("%d %d\n", m.focusedRow, m.focusedCol)

	// for row := range m.inputs {
	out += fmt.Sprintf(
		`%s %s %s %s`,
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

	out += fmt.Sprintf(
		`%s %s %s %s %s`,
		inputStyle.Width(30+3).Render("Title"),
		inputStyle.Width(15+3).Render("Tags"),
		inputStyle.Width(15+3).Render("Project"),
		inputStyle.Width(6+3).Render("Start"),
		inputStyle.Width(6+3).Render("End"),
	) + "\n"

	previous_day := ""
	for row := range m.oldData {
		note := gn.GetNoteById(pmm.NoteId(m.oldData[row][internal_id].Value()))
		start_time, _ := note.GetStartEndTime("start")
		start_date := start_time.Format("2006-01-02")

		if start_date != previous_day {
			out += fmt.Sprintf("\n%s\n", start_date)
			previous_day = start_date
		}

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
	} else if m.focusedRow == 1 {
		if len(m.oldData) == 0 {
			m.focusedRow = 0
			m.focusedCol = 0
		} else {
			m.focusedRow++
		}
	} else {
		if m.focusedRow == len(m.oldData)+1 {
			m.focusedRow = 0
			m.focusedCol = 0
		} else {
			if m.focusedCol+1 == 4 {
				m.focusedCol = 0
				m.focusedRow++
			} else {
				m.focusedCol++
			}
		}
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
		// WithAltScreen ⇒ 'fullscreen'
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
