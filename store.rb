require 'json'
require 'fileutils'

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

  def read(id)
    JSON.parse(File.read(id_to_path(id))).update({ 'id' => id })
  end

  # List all notes
  # @return [Array] list of note ids
  def list
    Dir["#{@location}/**/*"].select { |f| File.file?(f) }.map{ |x| File.basename x }
  end

  # List top level notes, those without an @parent
  def list_top_level
    list
      .map { |id| read(id) }
      .select { |note| note['parents'] == nil || note['parents'].empty? }
  end

  private
  def id_to_path(id)
    "#{@location}/#{id[0]}/#{id[1]}/#{id}"
  end
end
