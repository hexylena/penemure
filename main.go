package main

import (
	// "os"
	// "strings"
	// "fmt"
	// tea "github.com/charmbracelet/bubbletea"
	// "github.com/charmbracelet/lipgloss"
	"github.com/hexylena/pm/cmd"
	pmm "github.com/hexylena/pm/models"
	// tui "github.com/hexylena/pm/tui"
)

var globalNotes pmm.GlobalNotes

func main() {
	globalNotes = pmm.NewGlobalNotes()
	LoadNotes()
	round()

	// db := pmm.InitDB()
	// tui.StartTea()
	cmd.Execute(globalNotes)
	SaveNotes()
}
