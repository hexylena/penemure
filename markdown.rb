require 'redcarpet'
require 'json'

def parse_multiline_json(str)
  str.gsub!("}{", "}\n{")
  str.split("\n").map do |line|
    JSON.parse(line)
  end
end

# Create a custom renderer that sets a custom class for block-quotes.
class CustomRender < Redcarpet::Render::HTML
  def block_code(code, language)
    {
      :type => "code",
      :language => language,
      :contents => code,
    }.to_json
  end

  def block_quote(quote)
    {
      :type=> "blockquote",
      :contents=> quote
    }.to_json
  end

  def block_html(raw_html)
    {
      :type=> "html",
      :contents=> raw_html
    }.to_json
  end

  def footnotes(content)
    raise "Footnotes not supported"
  #   {
  #     :type=> "footnotes",
  #     :contents=> content
  #   }.to_json
  end
  #
  def footnote_def(content, number)
    raise "Footnotes not supported"
  end

  def header(text, header_level)
    {
      :type=> "h#{header_level}",
      :contents=> text
    }.to_json
  end

  def hrule()
    {
      :type=> "hr"
    }.to_json
  end

  def list(contents, list_type)
    {
      :type => list_type.match(/unordered/) ? "ul" : "ol",
      :contents => parse_multiline_json(contents),
    }.to_json
  end

  def list_item(text, list_type)
    {
      :type => "li",
      :contents => text,
    }.to_json
  end

  def paragraph(text)
    {
      :type => "p",
      :contents => text,
    }.to_json
  end

  def table(header, body)
    raise "Tables not supported"
  end

  def table_row(content)
    raise "Tables not supported"
  end

  def table_cell(content, alignment, header)
    raise "Tables not supported"
  end

end

class BlockRenderer
  def render(block)
    case block[:type]
      when "code"
        block_code(block)
      when "blockquote"
        block_quote(block)
      when "html"
        block_html(block)
      when "footnotes"
        footnotes(block)
      when "footnote_def"
        footnote_def(block)
      when "h1", "h2", "h3", "h4", "h5", "h6"
        header(block)
      when "hr"
        hrule(block)
      when "ul", "ol"
        list(block)
      when "li"
        list_item(block)
      when "p"
        paragraph(block)
      when "table"
        table(block)
      when "tr"
        table_row(block)
      when "td", "th"
        table_cell(block)
      else
        raise "Unknown block type: #{block[:type]}"
    end
  end

  def block_code(block)
    "```#{block[:language]}\n#{block[:contents]}\n```"
  end

  def block_quote(block)
    "> #{block[:contents]}"
  end

  def block_html(block)
    block[:contents]
  end

  def footnotes(content)
    raise "Footnotes not supported"
  end

  def footnote_def(content, number)
    raise "Footnotes not supported"
  end

  def header(block)
    "#{"#" * block[:type].match(/h(\d)/)[1].to_i} #{block[:contents]}"
  end

  def hrule(_)
    "---"
  end

  def list(block)
    if block[:type] == "ul"
      block[:contents].map do |item|
        "  * #{item[:contents]}"
      end.join("\n")
    else
      block[:contents].map.with_index do |item, i|
        "  #{i + 1}. #{item[:contents]}"
      end.join("\n")
    end
  end

  def list_item(text, list_type)
    "???"
  end

  def paragraph(block)
    block[:contents]
  end

  def table(block)
    raise "Tables not supported"
  end

  def table_row(block)
    raise "Tables not supported"
  end

  def table_cell(block)
    raise "Tables not supported"
  end
end

def parse_markdown(str)
  markdown = Redcarpet::Markdown.new(CustomRender, fenced_code_blocks: true)
  parse_multiline_json(markdown.render(str))
end

def render_markdown(blocks)
  bl = BlockRenderer.new
  (blocks || []).map do |block|
    block = block.transform_keys(&:to_sym)
    puts "Rendering #{block}"
    bl.render(block)
  end.join("\n")
end

def render_markdown_html(blocks)
  renderer = Redcarpet::Render::HTML.new
  markdown = Redcarpet::Markdown.new(renderer, extensions = {})
  (blocks || []).map do |block|
    block = block.transform_keys(&:to_sym)
    puts "Rendering 2 html #{block}"
    markdown.render(BlockRenderer.new.render(block))
  end.join("\n")
end
