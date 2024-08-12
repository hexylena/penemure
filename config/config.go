package config

import (
	"encoding/json"

	"fmt"

	pml "github.com/hexylena/pm/log"
	"github.com/spf13/viper"
)

type HxpmConfig struct {
	Title string
	About string

	// Adapter is how /where tasks are written
	Adapter       string
	AdapterConfig map[string]string

	// Export
	ExportDirectory      string
	ExportUseGoogleFonts bool
	ExportPrefix         string
	ServerBindAddr       string

	// Queries
	QueryHomepage       string
	QueryHomepageLayout string
	QueryChildren       string
	QueryChildrenLayout string
}

func setDefaults() {
	viper.SetDefault("Title", "HXPM")
	viper.SetDefault("About", "An awful project management tool")

	viper.SetDefault("Adapter", "fs")
	viper.SetDefault("AdapterConfig.Path", "./projects")

	viper.SetDefault("ExportDirectory", "./export")
	viper.SetDefault("ExportUseGoogleFonts", false)
	viper.SetDefault("ExportPrefix", "/")
	viper.SetDefault("ServerBindAddr", "127.0.0.1:3333")

	viper.SetDefault("QueryHomepage", "select title, created, Author from notes where parent is null GROUP BY type ORDER BY created")
	viper.SetDefault("QueryChildren", "select title, created, Author from notes where parent = 'NOTE_ID' group by type order by created")

	viper.SetDefault("QueryHomepageLayout", "table")
	viper.SetDefault("QueryChildrenLayout", "table")
}

func Init() HxpmConfig {
	// setup env
	viper.SetEnvPrefix("HXPM")
	viper.AutomaticEnv()

	// Load config
	viper.SetConfigName("config") // name of config file (without extension)
	viper.SetConfigType("yaml")   // REQUIRED if the config file does not have the extension in the name

	setDefaults()

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

	globalConfig := HxpmConfig{
		Adapter:              viper.GetString("Adapter"),
		Title:                viper.GetString("Title"),
		About:                viper.GetString("About"),
		ExportDirectory:      viper.GetString("ExportDirectory"),
		ExportUseGoogleFonts: viper.GetBool("ExportUseGoogleFonts"),
		ExportPrefix:         viper.GetString("ExportPrefix"),
		ServerBindAddr:       viper.GetString("ServerBindAddr"),

		QueryHomepage:       viper.GetString("QueryHomepage"),
		QueryHomepageLayout: viper.GetString("QueryHomepageLayout"),
		QueryChildren:       viper.GetString("QueryChildren"),
		QueryChildrenLayout: viper.GetString("QueryChildrenLayout"),
	}

	return globalConfig
}

func (config *HxpmConfig) Manifest() []byte {
	icon := map[string]string{
		"src":   config.ExportPrefix + "assets/favicon@256.png",
		"type":  "image/png",
		"sizes": "256x256",
	}
	data := map[string]interface{}{
		"background_color": "#ffffff",
		"name":             config.Title,
		"description":      config.About,
		"display":          "standalone",
		"scope":            config.ExportPrefix, // TODO: make this configurable
		"icons":            []map[string]string{icon},
		"start_url":        config.ExportPrefix, // TODO:
		"theme_color":      "#CE3518",
	}
	ret, err := json.Marshal(data)
	if err != nil {
		pml.L("conig").Error("Error", "err", err)
	}
	return ret
}
