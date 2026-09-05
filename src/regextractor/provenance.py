from __future__ import annotations

from typing import List, Optional

from .models import PageBlock


def page_text(blocks: List[PageBlock], pdf_page: int) -> str:
    parts = [b.text for b in blocks if b.pdf_page == pdf_page]
    return "\n".join(parts)


def evidence_on_cited_pages(excerpt: str, pages: List[int], blocks: List[PageBlock]) -> bool:
    if not excerpt or excerpt == "N/A":
        return False
    needle = " ".join(excerpt.split())[:80]
    if not needle:
        return False
    for p in pages:
        hay = " ".join(page_text(blocks, p).split())
        if needle[:40] in hay:
            return True
    return False


def printed_for_pages(blocks: List[PageBlock], pages: List[int]) -> Optional[int]:
    for b in blocks:
        if b.pdf_page in pages and b.printed_page is not None:
            return b.printed_page
    return None



def printed_pages_for(blocks: List[PageBlock], pages: List[int]) -> List[int]:
    out: List[int] = []
    for b in blocks:
        if b.pdf_page in pages and b.printed_page is not None and b.printed_page not in out:
            out.append(b.printed_page)
    return out


def spans_reconstruct_text(text: str, spans, blocks: List[PageBlock]) -> bool:
    if not text:
        return False
    cited_ids = {s.block_id for s in spans} if spans else set()
    cited_blocks = [b for b in blocks if b.block_id in cited_ids] if cited_ids else blocks
    hay = " ".join(" ".join(b.text.split()) for b in cited_blocks)
    needle = " ".join(text.split())
    if needle and needle in hay:
        return True
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    block_hays = [" ".join(b.text.split()) for b in cited_blocks]
    return all(any(line in hay or " ".join(line.split()) in hay for hay in block_hays) for line in lines)
