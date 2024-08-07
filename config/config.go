package config

import (
	"encoding/json"

	pml "github.com/hexylena/pm/log"
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
	ServerBindAddr string
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
