import re
from html import escape
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit


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


class _SafeArticleHtmlParser(HTMLParser):
    allowed_tags = {
        'a', 'b', 'blockquote', 'br', 'cite', 'code', 'del', 'em', 'figcaption',
        'figure', 'h2', 'h3', 'h4', 'hr', 'i', 'img', 'li', 'ol', 'p', 's',
        'strong', 'u', 'ul',
    }
    void_tags = {'br', 'hr', 'img'}

    def __init__(self, base_url=None):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.html_parts = []
        self.skip_depth = 0

    def _safe_url(self, value):
        if not value:
            return None
        resolved_url = urljoin(self.base_url or '', value.strip())
        if urlsplit(resolved_url).scheme not in {'http', 'https'}:
            return None
        return resolved_url

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.skip_depth += 1
            return
        if self.skip_depth or tag not in self.allowed_tags:
            return

        attributes = dict(attrs)
        if tag == 'a':
            href = self._safe_url(attributes.get('href'))
            if href:
                self.html_parts.append(
                    f'<a href="{escape(href, quote=True)}" target="_blank" '
                    'rel="noopener noreferrer">'
                )
                return
        elif tag == 'img':
            src = self._safe_url(attributes.get('src'))
            if src:
                alt = escape(attributes.get('alt', ''), quote=True)
                self.html_parts.append(
                    f'<img src="{escape(src, quote=True)}" alt="{alt}" loading="lazy">'
                )
                return
            return

        self.html_parts.append(f'<{tag}>')

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.void_tags:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if tag in {'script', 'style'} and self.skip_depth:
            self.skip_depth -= 1
            return
        if not self.skip_depth and tag in self.allowed_tags and tag not in self.void_tags:
            self.html_parts.append(f'</{tag}>')

    def handle_data(self, data):
        if not self.skip_depth:
            self.html_parts.append(escape(data))


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


def sanitize_article_html(content, base_url=None):
    clean_content, source_url = split_article_source(content)
    if source_url:
        decoded_content = unescape(content or '')
        source_marker = decoded_content.rfind('(Fonte original:')
        if source_marker >= 0:
            content = decoded_content[:source_marker].rstrip()

    parser = _SafeArticleHtmlParser(base_url=base_url)
    parser.feed(unescape(content or ''))
    parser.close()
    return ''.join(parser.html_parts).strip()


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
