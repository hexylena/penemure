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
var globalAdapter pma.TaskAdapter

func main() {
	logger := pml.L("main")
	logger.Info("Starting pm")

	globalAdapter := &pma.FsAdapter{
		Path: "./projects",
	}

	globalNotes = pmm.NewGlobalNotes()
	globalAdapter.LoadNotes(globalNotes)

	// db := pmm.InitDB()
	// tui.StartTea()
	logger.Info("Executing Command")
	cmd.Execute(globalNotes, globalAdapter)

	logger.Info("Shutting Down and Saving Notes")
	globalAdapter.SaveNotes(globalNotes)

}
