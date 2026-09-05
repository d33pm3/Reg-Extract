from pathlib import Path

import pytest

from regextractor.models import PageBlock


def wrap_md(pages):
    lines = ["<!-- SOURCE_ENGINE: fixture -->", ""]
    blocks = []
    for i, (page, printed, text) in enumerate(pages, start=1):
        lines.append(f"<!-- PDF_PAGE:{page} PRINTED_PAGE:{printed or ''} -->")
        lines.append(text)
        lines.append("")
        blocks.append(
            PageBlock(
                block_id=f"fix-{i}",
                pdf_page=page,
                printed_page=printed,
                text=text,
                heading_context="",
                source_engine="fixture",
            )
        )
    return "\n".join(lines), blocks
