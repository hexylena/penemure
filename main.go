package main

import (
	"github.com/spf13/viper"
	// "os"
	// "strings"

	// tea "github.com/charmbracelet/bubbletea"
	// "github.com/charmbracelet/lipgloss"
	"embed"

	pma "github.com/hexylena/pm/adapter"
	"github.com/hexylena/pm/cmd"
	pmc "github.com/hexylena/pm/config"
	pml "github.com/hexylena/pm/log"
	pmm "github.com/hexylena/pm/models"
	// tui "github.com/hexylena/pm/tui"
	// "os"
	// "runtime/debug"
)

var globalNotes pmm.GlobalNotes
var globalAdapter pma.TaskAdapter
var globalConfig pmc.HxpmConfig

//go:embed templates/* assets/*
var templateFS embed.FS

func main() {
	logger := pml.L("main")
	logger.Info("Starting pm")

	globalConfig := pmc.Init()

	var globalAdapter pma.TaskAdapter
	if globalConfig.Adapter == "fs" {
		globalAdapter = &pma.FsAdapter{
			Path: viper.GetString("AdapterConfig.Path"),
		}
	} else {
		panic("Unknown adapter")
	}

	globalNotes = pmm.NewGlobalNotes()
	globalAdapter.LoadNotes(globalNotes)

	// db := pmm.InitDB()
	// tui.StartTea()
	logger.Info("Executing Command")
	cmd.Execute(globalNotes, globalAdapter, globalConfig, templateFS)

	logger.Info("Shutting Down and Saving Notes")
	globalAdapter.SaveNotes(globalNotes)

}
