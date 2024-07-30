package cmd

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
	pma "github.com/hexylena/pm/adapter"
	"github.com/spf13/cobra"
	"os"
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

func Execute(notes pmm.GlobalNotes, adapter pma.TaskAdapter) {
	gn = notes
	ga = adapter
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
