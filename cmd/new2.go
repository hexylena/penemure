package cmd

import (
	// "errors"
	"github.com/spf13/cobra"
	"sort"
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

		var projects []huh.Option[string]
		for _, project := range gn.GetProjects() {
			projects = append(projects, huh.NewOption(project.Title, fmt.Sprintf("%s", project.NoteId)))
		}

		var parents_out []string
		var blocking_out []string
		var base16 *huh.Theme = huh.ThemeBase16()

		all_tasks := gn.GetNotes()

		// Start sorting nonsense
		type kv struct {
			Key   pmm.NoteId
			Value *pmm.Note
		}

		var ss []kv
		for k, v := range all_tasks {
			ss = append(ss, kv{k, v})
		}

		sort.Slice(ss, func(i, j int) bool {
			return ss[i].Value.Type+ss[i].Value.Title > ss[j].Value.Type+ss[j].Value.Title
		})
		// end sorting.

		var all_tasks_options1 []huh.Option[string]
		var all_tasks_options2 []huh.Option[string]
		for _, kv := range ss {
			t := fmt.Sprintf("%s %s", kv.Value.GetEmoji(), kv.Value.Title)
			all_tasks_options1 = append(all_tasks_options1, huh.NewOption(t, kv.Value.NoteId.String()))
			all_tasks_options2 = append(all_tasks_options2, huh.NewOption(t, kv.Value.NoteId.String()))
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
						huh.NewOption("File", "file"),
					).
					Value(&note.Type),
				huh.NewMultiSelect[string]().
					Options(all_tasks_options1...).
					Title("Parents").
					Value(&parents_out),
				// huh.NewMultiSelect[string]().
				// 	Options(all_tasks_options2...).
				// 	Title("Blocking").
				// 	Value(&blocking_out),
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
		gn.RegisterNote(note)
		fmt.Println(note)

		// gn.new2Edit()
	},
}
