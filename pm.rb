#!/usr/bin/env ruby
require 'yaml'
require 'tempfile'
require 'thor'
require './projects'
require './markdown'

PMZ = ProjectManager.new

# class Tasks < Thor
#   class_option :verbose, :type => :boolean, :aliases => "-v"
#
#   desc "list", "list tasks"
#   def list
#     puts "I'm a thor task!"
#   end
# end
#
# class Projects < Thor
#   class_option :verbose, :type => :boolean, :aliases => "-v"
#
# end

class PmCLI < Thor
  class_option :verbose, :type => :boolean, :aliases => "-v"

  # desc "t SUBCOMMAND", "Tasks"
  # subcommand "t", Tasks
  #
  desc "list", "list notes"
  def list
    PMZ.list_top_level
  end

  desc "show", "show notes <id>"
  def show(id)
    PMZ.show_project(id)
  end

  desc "new_note TITLE", "new notes <title>"
  def new_note(title)
    blocks = ""
    # Get a tempfile
    Tempfile.open('pm') do |f|
      # Initialize the tempfile with the template
      f.write("---\n")
      f.write("tags:\n")
      f.write("#   Asignee: []\n")
      f.write("#   Status: \"not started\"\n")
      f.write("#   Due: null\n")
      f.write("#   Priority: null\n")
      f.write("#   Tags: [\"writing\"]\n")
      f.write("#   URL: \"...\"\n")
      f.write("---\n")
      f.write("\n")
      f.write("## Write some content\n")
      f.flush
      # open vim for the user
      system("vim #{f.path}")
      # read the contents of the tempfile
      # and assign it to the blocks variable
      f.rewind

      blocks = f.read
    end
    p blocks
    # Split up the blocks, first the metadata
    parts = blocks.split("---\n")
    clean_yaml = parts[1].strip.split("\n").reject { |l| l.start_with?('#') }.join("\n")
    puts "#{clean_yaml}"
    # parse metadata as yaml
    meta = YAML.load(clean_yaml)
    # parse the rest as markdown
    blocks = parts[2..-1].join("---\n")
    parsed_blocks = parse_markdown(blocks)
    PMZ.create_note(title, nil, meta, parsed_blocks)
  end
end

PmCLI.start(ARGV)

