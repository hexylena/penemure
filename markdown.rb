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


def parse_markdown(str)
  markdown = Redcarpet::Markdown.new(CustomRender, fenced_code_blocks: true)
  parse_multiline_json(markdown.render(str))
end
