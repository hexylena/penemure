package cmd

import (
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(listCmd)

}

var listCmd = &cobra.Command{
	Use:   "list [project]",
	Short: "List all items, optionally filtered by project",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		gn.BubblePrint()
	},
}
