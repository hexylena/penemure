package cmd

import (
	"fmt"
	pmm "github.com/hexylena/pm/models"
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

func Execute(notes pmm.GlobalNotes) {
	gn = notes
	if err := rootCmd.Execute(); err != nil {
		fmt.Println(err)
		os.Exit(1)
	}
}
