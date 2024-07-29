package main

import (
	// "os"
	// "strings"
	// "fmt"
	// tea "github.com/charmbracelet/bubbletea"
	// "github.com/charmbracelet/lipgloss"
	pma "github.com/hexylena/pm/adapter"
	"github.com/hexylena/pm/cmd"
	pml "github.com/hexylena/pm/log"
	pmm "github.com/hexylena/pm/models"
	// tui "github.com/hexylena/pm/tui"
	// "os"
	// "runtime/debug"
)

var globalNotes pmm.GlobalNotes

func main() {
	logger := pml.L("main")
	logger.Info("Starting pm")

	globalNotes = pmm.NewGlobalNotes()
	pma.LoadNotes(globalNotes)
	round()

	// db := pmm.InitDB()
	// tui.StartTea()
	logger.Info("Executing Command")
	cmd.Execute(globalNotes)

	logger.Info("Shutting Down and Saving Notes")
	pma.SaveNotes(globalNotes)

}
