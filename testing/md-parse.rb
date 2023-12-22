require './markdown.rb'


output = parse_markdown("
# Testing

aasdf

## Subheading

blah

### Subsub heading

1. asdf
2. asdf
3. asdf

- asdf
- asdf
- asdf
")


pp output
