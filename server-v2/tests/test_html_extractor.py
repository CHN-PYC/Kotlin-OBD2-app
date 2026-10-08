import pytest

from app.services.knowledge.html_extractor import extract_hella_article


def page(body: str) -> str:
    return f"""<main class="webRoot">
      <div class="mod-headline-fs"><h1>Example sensor</h1></div>
      <div class="mod-notification-banner-fs">
      <div class="alert-text"><p>Qualified personnel only.</p></div></div>
      <div class="alert-text">Feedback noise</div>
      <nav><p>Navigation noise</p></nav>
      <div class="table-of-content"><li>Contents noise</li></div>
      <div class="mod-instruction-navigation-refactor-fs__anchor-target">{body}</div>
      <div><h2>Recommendations</h2><p>Advertisement noise</p></div>
    </main>"""


def test_preserves_headings_lists_and_order_without_duplicate_paragraphs() -> None:
    article = extract_hella_article(
        page("""<h2>Checks</h2><p>Before starting.</p>
      <h3>First step</h3><p><p>Check the <b>connector</b>.</p></p>
      <h3>Second step</h3><ul><li>Check A</li><li>Check B</li></ul>""")
    )
    assert [b.kind for b in article.blocks] == ["paragraph", "paragraph", "list_item", "list_item"]
    assert article.blocks[1].heading_path == ["Example sensor", "Checks", "First step"]
    assert [b.text for b in article.blocks[-2:]] == ["Check A", "Check B"]
    assert article.blocks[-1].heading_path[-1] == "Second step"
    assert article.safety_notes == ["Qualified personnel only."]
    assert "noise" not in article.model_dump_json()


def test_skips_video_section_and_scripts() -> None:
    html = page("<h2>Checks</h2><p>Keep &amp; verify.</p><script>bad()</script>")
    html = html.replace(
        "</main>",
        """
      <div class="mod-instruction-navigation-refactor-fs__anchor-target">
      <h2>Video</h2><div class="mod-video-fs"></div><p>Video teaser</p></div></main>""",
    )
    article = extract_hella_article(html)
    assert [b.text for b in article.blocks] == ["Keep & verify."]


@pytest.mark.parametrize(
    "html",
    [
        "",
        "<html><p>Not an article</p></html>",
        '<main class="webRoot"><h1>Changed layout</h1></main>',
        page("<h2>Empty section</h2>"),
        page("<p>Missing section heading</p>"),
    ],
)
def test_rejects_missing_or_empty_article(html: str) -> None:
    with pytest.raises(ValueError):
        extract_hella_article(html)
