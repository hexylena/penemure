#!/usr/bin/env ruby
require 'yaml'
require 'thor'
require './projects'

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
    PMZ.show_note(id)
  end

  desc "edit ID", "edit note <id>"
  def edit(id)
    PMZ.edit_note(id)
  end

  desc "debug ID", "debug note <id>"
  def debug(id)
    PMZ.debug(id)
  end

  desc "delete ID", "delete note <id>"
  def delete(id)
    PMZ.delete(id)
  end

  desc "notion_import path", "notion_import <id>"
  def notion_import(id)
    PMZ.notion_import(id)
  end

  desc "export", "export"
  def export
    PMZ.export
  end

  desc "new_note", "new notes"
  def new_note
    blocks = ""
    # Get a tempfile
    require 'tempfile'
    Tempfile.open('pm') do |f|
      # Initialize the tempfile with the template
      f.write("---\n")
      f.write("title: New Note\n")
      f.write("tags:\n")
      f.write("#   Assignee: []\n")
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

    (_, title, parents, tags, parsed_blocks) = PMZ.parse_markdown_note blocks
    pp "title: #{title}"
    pp "parents: #{parents}"
    pp "tags: #{tags}"
    pp "parsed_blocks: #{parsed_blocks}"

    PMZ.create_note(title, parents, tags, parsed_blocks)
  end
end

PmCLI.start(ARGV)

