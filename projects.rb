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

  def note(title, parents, tags, blocks)
    if tags.is_a? Hash
      tags = tags.map { |t| { 'title' => t[0], 'value' => t[1], 'type' => discover_type(title), 'icon' => nil  } }
    end

    note = {
      'title' => title,
      'parents' => parents || nil,
      '_tags' => tags,
      '_blocks' => blocks,
    }
  end

  # Create a new note
  # @param [String] title
  # @param [Array] parents
  # @param [Hash] tags (1 level deep only)
  # @param [String] blocks
  def create_note(title, parents, tags, blocks)
    # Should we do validation?
    @store.create(note(title, parents, tags, blocks))
  end

  def list_top_level
    require 'tty-table'
    table = TTY::Table.new(header: ['ID', 'Title', 'Status', 'Tags'])
    @store.list_top_level.each do |note|
      table << [
        note['id'],
        note['title'],
        note['_tags'].select{|t| t['title'] == 'Status'}.first['value'],
        note['_tags'].select{|t| t['title'] == 'Tags'}.first['value'].join(', '),
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
    # Cleanup
    meta.delete('id')
    meta.delete('title')
    meta.delete('parents')
    tags = meta['tags'] || meta['_tags']

    [id, title, parents, tags, parsed_blocks]
  end

  def render_markdown_note(n)
    res = ""
    res += {
        'id' => n['id'],
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
        'parents' => nil,
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
      system("vim +3 #{f.path}")

      # Back to the beginning
      f.rewind
      text = f.read

      (id, title, parents, tags, parsed_blocks) = parse_markdown_note(text)

      @store.update(id, note(title, parents, tags, parsed_blocks))
    end
  end

  def debug(id_partial)
    n = get_note_by_partial_id(id_partial)
    pp n
  end

  def show_note(id_partial)
    n = get_note_by_partial_id(id_partial)
    puts "Title: #{n['title']}"
    if n['parents']
      puts "Parents: #{n['parents']}"
    end
    if n['_tags']
      n['_tags'].each do |tag|
        puts "#{tag['title']}: #{tag['value']}"
      end
    end

    if n['_blocks']
      require 'tty-markdown'
      puts TTY::Markdown.parse(render_markdown(n['_blocks']))
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
