import re
from html import unescape
from html.parser import HTMLParser


class _ArticleContentParser(HTMLParser):
    block_tags = {'article', 'br', 'div', 'li', 'p'}
    inline_tags = {
        'a', 'abbr', 'b', 'bdi', 'bdo', 'cite', 'code', 'del', 'dfn',
        'em', 'i', 'ins', 'kbd', 'mark', 'q', 's', 'samp', 'small', 'span',
        'strong', 'sub', 'sup', 'time', 'u', 'var',
    }

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
        elif not self.skip_depth and tag in self.inline_tags:
            self.text_parts.append(' ')

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self.skip_depth:
            self.skip_depth -= 1
        elif not self.skip_depth and tag in self.block_tags:
            self.text_parts.append('\n')
        elif not self.skip_depth and tag in self.inline_tags:
            self.text_parts.append(' ')

    def handle_data(self, data):
        if not self.skip_depth:
            self.text_parts.append(data)


def extract_article_content(content):
    parser = _ArticleContentParser()
    parser.feed(unescape(content or ''))
    parser.close()

    text = ''.join(parser.text_parts)
    text = re.sub(r'[ \t\f\v]+', ' ', text)
    text = re.sub(r' *\n *', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' +([,.;:!?])', r'\1', text)

    return text.strip(), parser.image_url


def split_article_source(content):
    clean_content = extract_article_content(content)[0]
    source_match = re.search(
        r'\s*\(Fonte original:\s*(https?://[^\s)]+)\)\s*$',
        clean_content,
        flags=re.IGNORECASE,
    )
    if not source_match:
        return clean_content, None

    return clean_content[:source_match.start()].rstrip(), source_match.group(1)


def clean_article_content(content):
    return split_article_source(content)[0]
