import re
from html import unescape
from html.parser import HTMLParser


class _ArticleContentParser(HTMLParser):
    block_tags = {'article', 'br', 'div', 'li', 'p'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text_parts = []
        self.image_url = None
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'img' and not self.image_url:
            self.image_url = unescape(attributes.get('src', '')) or None

        if tag in {'script', 'style'}:
            self.skip_depth += 1
        elif not self.skip_depth and tag in self.block_tags:
            self.text_parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in self.block_tags:
            self.text_parts.append('\n')

    def handle_data(self, data):
        if not self.skip_depth:
            self.text_parts.append(data)


def extract_article_content(content):
    parser = _ArticleContentParser()
    parser.feed(content or '')
    parser.close()

    text = ''.join(parser.text_parts)
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip(), parser.image_url


def clean_article_content(content):
    return extract_article_content(content)[0]
