require 'json'
require 'fileutils'
require './types.rb'

# Store notes in a json file
class JsonAdapter
  def initialize(location)
    @location = location
    # if location isn't a folder, create it
    Dir.mkdir(location) unless File.exist?(location)
  end

  # Create a new note
  # @param [Hash] note
  # @return [str] id of the note
  def create(note)
    require 'securerandom'
    id = SecureRandom.uuid
    # Create the folder if needed
    unless File.exist?(File.dirname(id_to_path(id)))
      FileUtils.mkpath(File.dirname(id_to_path(id)))
    end

    File.open(id_to_path(id), 'w') do |file|
      note['id'] = id
      file.write(note.to_json)
    end
    id
  end

  def update(id, note)
    File.open(id_to_path(id), 'w') do |file|
      file.write(note.to_json)
    end
  end

  def delete(id)
    File.delete(id_to_path(id))
  end

  def _read(id)
    JSON.parse(File.read(id_to_path(id))).update({ 'id' => id })
  end

  def read(id)
    n = _read(id)
    Note.new(n['title'], n['parents'], n['_tags'], n['_blocks'], n['id'], n['type'])
  end

  # List all notes
  # @return [Array] list of note ids
  def list
    Dir["#{@location}/**/*"].select { |f| File.file?(f) }.map{ |x| File.basename x }
  end

  def list_notes
    list
      .map { |id| read(id) }
  end

  # List top level notes, those without an @parent
  def list_top_level
    list_notes
      .select { |note| note.parents.empty? }
  end

  def find_by_title(title)
    list
      .map { |id| read(id) }
      .select { |note| note.title == title }
      .first
  end

  private
  def id_to_path(id)
    "#{@location}/#{id[0]}/#{id[1]}/#{id}"
  end
end
