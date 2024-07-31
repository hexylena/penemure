package config

type HxpmConfig struct {
	Title string
	About string

	// Adapter is how /where tasks are written
	Adapter string
	AdapterConfig map[string]string

	// Export
	ExportDirectory string
}
