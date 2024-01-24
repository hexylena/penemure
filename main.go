package main

import (
	// "os"
	// "strings"
	// "fmt"
	// tea "github.com/charmbracelet/bubbletea"
	// "github.com/charmbracelet/lipgloss"
	pma "github.com/hexylena/pm/adapter"
	"github.com/hexylena/pm/cmd"
	pmm "github.com/hexylena/pm/models"
	// tui "github.com/hexylena/pm/tui"
)

var globalNotes pmm.GlobalNotes

func main() {
	globalNotes = pmm.NewGlobalNotes()
	pma.LoadNotes(globalNotes)
	round()

	// db := pmm.InitDB()
	// tui.StartTea()
	cmd.Execute(globalNotes)
	pma.SaveNotes(globalNotes)

}
