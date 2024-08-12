package cmd

import (
	"github.com/spf13/cobra"
	"github.com/spf13/viper"
)

func init() {
	rootCmd.AddCommand(configExportCmd)

}

var configExportCmd = &cobra.Command{
	Use:   "config-export",
	Short: "config-export",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {
		viper.SafeWriteConfigAs("config.example.yaml")
	},
}
