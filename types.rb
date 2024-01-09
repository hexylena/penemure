class Note
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

  def initialize(title, parents, tags, blocks, id=nil, type)
    if tags.is_a? Hash
      tags = tags.map { |t| { 'title' => t[0], 'value' => t[1], 'type' => discover_type(title), 'icon' => nil  } }
    end
    @n = {
      'title' => title,
      'created' => Time.now.to_i,
      'parents' => parents || [],
      'type' => type,
      '_tags' => tags,
      '_blocks' => blocks,
      'id' => id,
    }
  end

  def self.from_store(n)
    @n = n
  end

  def to_json
    @n.to_json
  end

  def to_h
    @n
  end

  def id
    @n['id']
  end

  def title
    @n['title']
  end

  def type
    @n['type']
  end

  def parents
    @n['parents'] || []
  end

  def children(store)
    store.list_notes.select { |n| n.parents.include? @n['id'] }
  end

  def tags
    @n['_tags'] || []
  end

  def blocks
    @n['_blocks'] || []
  end

  def get(key)
    begin
      @n['_tags'].select { |t| t['title'] == key }.first['value']
    rescue
      nil
    end
  end

end


