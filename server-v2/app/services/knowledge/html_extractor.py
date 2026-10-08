from typing import Literal

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    heading_path: list[str]
    kind: Literal["paragraph", "list_item"]
    text: str = Field(min_length=1)


class ExtractedArticle(BaseModel):
    title: str
    safety_notes: list[str]
    blocks: list[TextBlock]


def _text(tag: Tag) -> str:
    return " ".join(tag.get_text(" ", strip=True).split())


def _read_blocks(container: Tag, title: str) -> list[TextBlock]:
    headings = {1: title}
    blocks = []
    for tag in container.select("h2, h3, p, li"):
        # Nested <p> wrappers occur in this snapshot. Read the outer block only once.
        if tag.find_parent(["p", "li"]) is not None:
            continue
        text = _text(tag)
        if not text:
            continue
        if tag.name in {"h2", "h3"}:
            level = int(tag.name[1])
            headings = {key: value for key, value in headings.items() if key < level}
            headings[level] = text
        else:
            blocks.append(
                TextBlock(
                    heading_path=list(headings.values()),
                    kind="list_item" if tag.name == "li" else "paragraph",
                    text=text,
                )
            )
    return blocks


def extract_hella_article(html: str) -> ExtractedArticle:
    """Extract this HELLA article template, never fall back to whole-page text."""
    soup = BeautifulSoup(html, "html.parser")
    main = soup.select_one("main.webRoot")
    if main is None:
        raise ValueError("HELLA article container not found")
    for noise in main.select("script, style, iframe, nav, button, .table-of-content"):
        noise.decompose()
    titles = main.select(".mod-headline-fs h1")
    sections = main.select(".mod-instruction-navigation-refactor-fs__anchor-target")
    if len(titles) != 1 or not _text(titles[0]) or not sections:
        raise ValueError("HELLA article title or sections missing")
    title = _text(titles[0])
    blocks = []
    for intro in main.select(".mod-instruction-title-fs__text"):
        blocks.extend(_read_blocks(intro, title))
    section_blocks = []
    for section in sections:
        if section.select_one(".mod-video-fs") is not None:
            continue
        if section.select_one("h2") is None:
            raise ValueError("HELLA section heading missing")
        section_blocks.extend(_read_blocks(section, title))
    if not section_blocks:
        raise ValueError("HELLA article has no text sections")
    return ExtractedArticle(
        title=title,
        safety_notes=[
            _text(note)
            for note in main.select(".mod-notification-banner-fs .alert-text")
            if _text(note)
        ],
        blocks=blocks + section_blocks,
    )
