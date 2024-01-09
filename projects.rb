require './store.rb'


class ProjectManager
  def initialize
    @store = JsonAdapter.new 'projects'
  end

  # Create a new note
  # @param [String] title
  # @param [Array] parents
  # @param [Hash] tags (1 level deep only)
  # @param [String] blocks
  def create_note(title, parents, tags, blocks, type)
    # Should we do validation?
    q = Note.new(title, parents, tags, blocks, type)
    @store.create(q.to_h)
  end

  def list_top_level
    require 'tty-table'
    table = TTY::Table.new(header: ['Type', 'ID', 'Title', 'Status', 'Tags'])
    @store.list_top_level.each do |note|
      table << [
        note.type,
        note.id,
        note.title,
        note.get('Status'),
        note.get('Tags').join(', '),
      ]
    end
    puts table.render(:unicode)
  end

  def parse_markdown_note(text)
    # Split up the blocks, first the metadata
    parts = text.split("---\n")
    clean_yaml = parts[1].strip.split("\n").reject { |l| l.start_with?('#') }.join("\n")
    puts "#{clean_yaml}"
    # parse metadata as yaml
    meta = YAML.load(clean_yaml)
    # parse the rest as markdown
    blocks = parts[2..-1].join("---\n")
    require './markdown.rb'
    parsed_blocks = parse_markdown(blocks)

    id = meta['id']
    title = meta['title']
    parents = meta['parents']
    type = meta['type']
    # Cleanup
    meta.delete('id')
    meta.delete('title')
    meta.delete('parents')
    meta.delete('type')
    tags = meta['tags'] || meta['_tags']

    [id, title, parents, tags, parsed_blocks, type]
  end

  def render_markdown_note(n)
    res = ""
    res += {
        'id' => n['id'],
        'type' => n['type'],
        'title' => n['title'],
        'parents' => n['parents'],
        'tags' => (n['_tags'] || []).map{|x| [x['title'], x['value']]}.to_h,
      }.to_yaml
    res += "---\n\n"
    require './markdown.rb'
    res += render_markdown(n['_blocks'])
    res
  end

  def get_note_by_partial_id(id_partial)
    matches = @store.list_top_level.select { |x| x['id'].start_with?(id_partial) }
    if matches.length == 1
      n = @store.read(matches[0]['id'])
    elsif matches.length > 1
      raise "Multiple matches found, please restrict your ID. [#{matches.map{|x|x['id']}}]"
    else
      raise "No matches found"
    end
    n
  end

  def delete(id_partial)
    n = get_note_by_partial_id(id_partial)
    @store.delete(n['id'])
  end

  def edit_note(id_partial)
    if id_partial.nil?
      n = {
        'title' => 'New Note',
        'parents' => [],
        'type' => 'note',
        '_tags' => nil,
        '_blocks' => nil,
      }
    else
      n = get_note_by_partial_id(id_partial)
    end

    # Get a tempfile
    require 'tempfile'
    Tempfile.open('pm') do |f|
      f.write(render_markdown_note(n))
      f.flush

      # open vim for the user
      system("vim +4 #{f.path}")

      # Back to the beginning
      f.rewind
      text = f.read

      (id, title, parents, tags, parsed_blocks, type) = parse_markdown_note(text)

      n = Note.new(title, parents, tags, parsed_blocks, type=type)
      @store.update(id, n.to_h)
    end
  end

  def debug(id_partial)
    n = get_note_by_partial_id(id_partial)
    pp n
  end

  def show_note(id_partial)
    n = get_note_by_partial_id(id_partial)
    puts "Title: #{n['title']}"
    if n.parents
      puts "Parents: #{n.parents}"
    end
    if n['_tags']
      n['_tags'].each do |tag|
        puts "#{tag['title']}: #{tag['value']}"
      end
    end

    if n['_blocks']
      require 'tty-markdown'
      require './markdown.rb'
      puts TTY::Markdown.parse(render_markdown(n['_blocks']))
    end
  end

  def notion_import(path)
    # Find the '_all.csv' file
    require 'csv'

    def clean_notion(s)
      if ! s.nil?
        if s.include?(" (")
          s[0 .. s.rindex(" (") - 1]
        else
          s
        end
      else
        s
      end
    end

    csv_fn = Dir.glob("#{path}/*_all.csv").first
    csv = CSV.read(csv_fn, headers: true)
    to_process = []
    csv.each do |row|
      title = row['﻿Task'] # RIP
      # Find the task by ID
      parent_title = row['Parent-task']
      tags = {
        'Status' => row['Status'],
        'Project' => clean_notion(row['Project']),
        'Tags' => (row['Tags'] || '').split(',').push('notion-import'),
        'Priority' => row['Priority'],
        'Due' => row['Due'],
        'Assignee' => row['Assignee'],
        # 'Sub-tasks' => row['Sub-tasks'],
        'Blocked by' => row['Blocked by'],
        # 'Blocking' => row['Blocking'],
        'Estimates' => row['Estimates'],
        'ID' => row['ID'],
        'URL' => row['URL'],
      }
      blocks = nil

      to_process << [title, parent_title, tags, blocks, 'task']
    end

    # Parentless
    to_process.select{|x| x[1].nil?}.each do |(title, parent_title, tags, blocks, type)|
      parents = []
      if tags['Project']
        q = @store.find_by_title(tags['Project'])
        if q.nil?
          p "Adding project: #{clean_notion(tags['Project'])}"
          parents.push(create_note(
            clean_notion(tags['Project']), [], {'Tags' => ['notion-import']}, nil, 'project'))
        end
      end

      create_note(title, parents, tags, blocks, type)
    end

    # p '==='
    # With parents
    to_process.reject{|x| x[1].nil?}.each do |(title, parent_title, tags, blocks, type)|
      parent_title = clean_notion(parent_title)
      parent_node = @store.find_by_title(parent_title)
      create_note(title, [parent_node.id], tags, blocks, type)
    end


  end

  def export
    require 'erb'
    # Load templates/list.html
    template = File.read('templates/list.html.erb')
    # Get all the notes
    notes = @store.list_notes
    # Render the template
    renderer = ERB.new(template)
    p renderer

    # Store in output/ directory which may not exist
    Dir.mkdir('output') unless Dir.exist?('output')
    File.open('output/index.html', 'w') do |f|
      f.write(renderer.result(binding))
    end

    require './markdown.rb'

    template = File.read('templates/note.html.erb')
    renderer = ERB.new(template)
    Dir.mkdir('output/notes') unless Dir.exist?('output/notes')
    @store.list_notes.each do |note|
      File.open("output/notes/#{note.id}.html", 'w') do |f|
        f.write(renderer.result(binding))
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
