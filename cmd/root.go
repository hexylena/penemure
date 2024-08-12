// Package cmd provides command line utilites
package cmd

import (
	"fmt"
	"os"

	"embed"

	pma "github.com/hexylena/pm/adapter"
	pmc "github.com/hexylena/pm/config"
	pmm "github.com/hexylena/pm/models"
	pml "github.com/hexylena/pm/log"
	"github.com/spf13/cobra"
)

var rootCmd = &cobra.Command{
	Use:   "pm",
	Short: "A project manager",
	Run: func(cmd *cobra.Command, args []string) {
		// Do Stuff Here
	},
}

var gn pmm.GlobalNotes
var ga pma.TaskAdapter
var config pmc.HxpmConfig
var templateFS embed.FS
var logger = pml.L("cmd")

func Execute(notes pmm.GlobalNotes, adapter pma.TaskAdapter, _config pmc.HxpmConfig, templates embed.FS) {
	gn = notes
	ga = adapter
	config = _config
	templateFS = templates
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
