require 'json'
require 'console_table'
require './store.rb'


class ProjectManager
  def initialize
    @store = JsonAdapter.new 'projects'
  end

  def discover_type(title)
    case title
    when 'URL'
      'url'
    when 'Status'
      'select'
    when 'Priority'
      'select'
    when 'Due'
      'date'
    when 'Tags'
      'list'
    when 'Assignee'
      'list'
    else
      'text'
    end
  end

  # Create a new note
  # @param [String] title
  # @param [Array] parents
  # @param [Hash] tags (1 level deep only)
  # @param [String] blocks
  def create_note(title, parents, tags, blocks)
    note = {
      '@title' => title,
      '@parents' => parents || nil,
      '_tags' => tags.map { |t| { 'title' => t[0], 'value' => t[1], 'type' => discover_type(title), 'icon' => nil  } },
      '_blocks' => blocks,
    }
    # Should we do validation?
    @store.create(note)
  end

  def list_top_level
    @store.list_top_level.each do |note|
      p note
    end
  end

  def show_note(id)
    n = @store.read(id)
    puts "Title: #{n['@title']}"
    if n['@parents']
      puts "Parents: #{n['@parents']}"
    end
    if n['_tags']
      n['_tags'].each do |tag|
        puts "#{tag['title']}: #{tag['value']}"
      end
    end

    if n['_blocks']
      n['_blocks'].each do |block|
        # Render markdown into the terminal
        case block['type']
        when 'h1'
          puts TTY::Markdown.parse("# #{block['value']}")
        when 'h2'
          puts TTY::Markdown.parse("## #{block['value']}")
        when 'h3'
          puts TTY::Markdown.parse("### #{block['value']}")
        when 'p'
          puts TTY::Markdown.parse("#{block['value']}")
        when 'ul'
          puts TTY::Markdown.parse(block['value'].map { |x| "- #{x}" }.join("\n"))
        when 'ol'
          puts TTY::Markdown.parse(block['value'].map.with_index { |x, i| "#{i+1}. #{x}" }.join("\n"))
        when 'todo'
          puts TTY::Markdown.parse(block['value'].map { |x| "- [ ] #{x}" }.join("\n"))
        when 'code'
          puts TTY::Markdown.parse("```\n#{block['value']}\n```")
        when 'quote'
          puts TTY::Markdown.parse("> #{block['value']}")
        when 'hr'
          puts TTY::Markdown.parse("---")
        end

      end
    end

  end

end
    #
    #
    # - [ ] title (v0)
    # - [ ] description (v0)
    # - [ ] roles (v0)
    # - [ ] start/end dates (use this when showing date pickers) (v0)
    # - [ ] key resources (docs/pdfs/logos/etc.) (v1)
    # - [ ] Child projects with own sharing (v1)
    # - [ ] filter out blocked. (v0)
    # - [ ] Groups of Tasks - what did she mean by this? The world will never know.
