"""HTML → text with image markers, keeping question structure (one option per line)."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString

DROP = ["script", "style", "noscript", "nav", "header", "footer", "aside", "form", "iframe", "svg", "button"]
BLOCK = {"p", "div", "li", "br", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "ol", "ul", "table", "blockquote", "dd", "dt"}


def _main(soup):
    for sel in ("article", "main", "[role=main]", ".entry-content", ".post-content", "#content"):
        node = soup.select_one(sel)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    body = soup.body or soup
    best, best_len = body, 0
    for div in body.find_all(["div", "section"], recursive=True):
        n = len(div.get_text(strip=True))
        # prefer the smallest container that still holds most of the text
        if n > best_len * 1.0 and n > 300 and len(div.find_all(["div", "section"])) < 200:
            best, best_len = div, n
    return best if best_len else body


def html_to_text(html: str, base_url: str = "") -> tuple[str, str]:
    """Return (text, page_title)."""
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    for tag in soup(DROP):
        tag.decompose()
    root = _main(soup)
    for sup in root.find_all("sup"):
        sup.replace_with(f"^{sup.get_text()}")
    for sub in root.find_all("sub"):
        sub.replace_with(f"_{sub.get_text()}")
    for img in root.find_all("img"):
        src = img.get("data-src") or img.get("src") or ""
        if src and not src.startswith("data:"):
            img.replace_with(f" [[IMG:{urljoin(base_url, src)}]] ")
        else:
            img.decompose()
    parts = []

    def walk(node):
        for child in node.children:
            if isinstance(child, NavigableString):
                parts.append(str(child))
            elif child.name in BLOCK:
                parts.append("\n")
                walk(child)
                parts.append("\n")
            else:
                walk(child)

    walk(root)
    text = "".join(parts)
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n", text)
    return text.strip(), title
