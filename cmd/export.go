package cmd

import (
	"github.com/spf13/cobra"
)

func init() {
	rootCmd.AddCommand(exportCmd)

}

var exportCmd = &cobra.Command{
	Use:   "export",
	Short: "export as a static site",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		gn.Export(&config, &templateFS)
	},
}
