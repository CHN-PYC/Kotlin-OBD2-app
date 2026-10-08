from app.services.knowledge.html_extractor import TextBlock


def group_section_blocks(blocks: list[TextBlock]) -> list[list[TextBlock]]:
    """Group adjacent blocks by their first two headings, preserving order.

    Skip introduction blocks with only a document title. Reject empty heading
    paths. Return new group lists without modifying the input blocks.
    This groups candidate sections; it does not enforce chunk length limits.
    """
    # LEARNING: ':' annotates the variable type; '=' assigns its initial value.
    groups: list[list[TextBlock]] = []
    previous_key: list[str] | None = None
    for block in blocks:
        # An empty list is [], not None. Both are falsy, but they are different values.
        if not block.heading_path:
            raise ValueError("heading path is empty")
        if len(block.heading_path) == 1:
            # continue skips this block; break would stop reading the article.
            continue
        key = block.heading_path[:2]
        if key != previous_key:
            groups.append([])
            previous_key = key
        groups[-1].append(block)
    # Return after processing every block; empty input also returns [].
    return groups
