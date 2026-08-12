from __future__ import annotations

import re

from bs4 import BeautifulSoup


class ContentExtractor:
    def __init__(self, max_chars: int = 12_000) -> None:
        self.max_chars = max_chars

    def extract(self, html: str, fallback_title: str = "") -> tuple[str, str]:
        soup = BeautifulSoup(html, "html.parser")
        for node in soup(["script", "style", "noscript", "svg", "nav", "footer", "form"]):
            node.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else fallback_title
        root = soup.find("main") or soup.find("article") or soup.body or soup
        chunks: list[str] = []
        for node in root.find_all(["h1", "h2", "h3", "p", "li", "td"]):
            text = " ".join(node.get_text(" ", strip=True).split())
            if len(text) >= 30 and text not in chunks:
                chunks.append(text)
        if not chunks:
            text = " ".join(root.get_text(" ", strip=True).split())
            chunks = [text] if text else []
        body = re.sub(r"\s+", " ", "\n".join(chunks)).strip()
        return title[:300], body[: self.max_chars]
