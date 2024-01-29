package cmd

import (
	// "errors"
	"github.com/spf13/cobra"
	"strings"

	"fmt"
	"log"

	"github.com/charmbracelet/huh"
	pmd "github.com/hexylena/pm/md"
	pmm "github.com/hexylena/pm/models"
)

var (
	burger       string
	toppings     []string
	sauceLevel   int
	name         string
	instructions string
	discount     bool
)

func init() {
	rootCmd.AddCommand(new2Cmd)

}

var new2Cmd = &cobra.Command{
	Use:   "new2",
	Short: "new2",
	Args:  cobra.MaximumNArgs(1),
	Run: func(cmd *cobra.Command, args []string) {

		note := pmm.NewNote()
		gn.RegisterNote(note)

		var projects []huh.Option[string]
		for _, project := range gn.GetProjects() {
			projects = append(projects, huh.NewOption(project.Title, fmt.Sprintf("%s", project.NoteId)))
		}

		var projects_out []string
		var parents_out []string
		var blocking_out []string
		var base16 *huh.Theme = huh.ThemeBase16()

		all_tasks := gn.GetTasks()
		var all_tasks_options1 []huh.Option[string]
		var all_tasks_options2 []huh.Option[string]
		for _, task := range all_tasks {
			all_tasks_options1 = append(all_tasks_options1, huh.NewOption(task.Title, fmt.Sprintf("%s", task.NoteId)))
			all_tasks_options2 = append(all_tasks_options2, huh.NewOption(task.Title, fmt.Sprintf("%s", task.NoteId)))
		}

		var tags_out string
		var contents_out string

		form := huh.NewForm(
			huh.NewGroup(
				// Ask the user for a base burger and toppings.
				huh.NewInput().
					Title("Title").
					Value(&note.Title),
				huh.NewSelect[string]().
					Title("Note Type").
					Options(
						huh.NewOption("Project", "project"),
						huh.NewOption("Task", "task"),
						huh.NewOption("Note", "note"),
						huh.NewOption("Meeting", "meeting"),
						huh.NewOption("Log", "log"),
					).
					Value(&note.Type),
				huh.NewMultiSelect[string]().
					Options(projects...).
					Title("Projects").
					Value(&projects_out),
				huh.NewMultiSelect[string]().
					Options(all_tasks_options1...).
					Title("Parents").
					Value(&parents_out),
				huh.NewMultiSelect[string]().
					Options(all_tasks_options2...).
					Title("Blocking").
					Value(&blocking_out),
			),
			huh.NewGroup(
				huh.NewInput().
					Title("Tags").
					Value(&tags_out),
				huh.NewText().
					Title("Contents").
					Value(&contents_out),
			),
		).WithTheme(base16)
		err := form.Run()
		if err != nil {
			log.Fatal(err)
		}

		for _, project := range projects_out {
			note.Projects = append(note.Projects, pmm.NoteId(project))
		}

		for _, parent := range parents_out {
			note.Parents = append(note.Parents, pmm.NoteId(parent))
		}

		for _, blocking := range blocking_out {
			note.Blocking = append(note.Blocking, pmm.NoteId(blocking))
		}

		for _, tag := range strings.Split(tags_out, " ") {
			note.AddTag(tag)
		}

		note.Blocks = pmd.MdToBlocks([]byte(contents_out))
		fmt.Println(note)

		// gn.new2Edit()
	},
}
