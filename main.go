package main

import (
	"github.com/spf13/viper"
	// "os"
	// "strings"
	"fmt"
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

	// setup env
	viper.SetEnvPrefix("HXPM")
	viper.AutomaticEnv()

	// Load config
	viper.SetConfigName("config") // name of config file (without extension)
	viper.SetConfigType("yaml")   // REQUIRED if the config file does not have the extension in the name

	viper.SetDefault("Title", "HXPM")
	viper.SetDefault("About", "An awful project management tool")

	viper.SetDefault("Adapter", "fs")
	viper.SetDefault("AdapterConfig.Path", "./projects")
	viper.SetDefault("ExportDirectory", "./export")
	viper.SetDefault("ExportUseGoogleFonts", false)
	viper.SetDefault("ExportPrefix", "/")

	viper.SetDefault("ServerBindAddr", ":3333")

	viper.AddConfigPath(".") // path to look for the config file in
	// TODO: xdg paths.
	// viper.AddConfigPath("/etc/appname/")   // path to look for the config file in
	// viper.AddConfigPath("$HOME/.appname")  // call multiple times to add many search paths
	viper.AddConfigPath(".") // optionally look for config in the working directory
	if err := viper.ReadInConfig(); err != nil {
		if _, ok := err.(viper.ConfigFileNotFoundError); ok {
			// Config file not found; ignore error if desired
		} else {
			// Config file was found but another error was produced
			panic(fmt.Errorf("fatal error config file: %w", err))
		}
	}

	globalConfig = pmc.HxpmConfig{
		Adapter:              viper.GetString("Adapter"),
		Title:                viper.GetString("Title"),
		About:                viper.GetString("About"),
		ExportDirectory:      viper.GetString("ExportDirectory"),
		ExportUseGoogleFonts: viper.GetBool("ExportUseGoogleFonts"),
		ExportPrefix:         viper.GetString("ExportPrefix"),
		ServerBindAddr:       viper.GetString("ServerBindAddr"),
	}

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
