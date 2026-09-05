from __future__ import annotations

import re

CHAPTER_RE = re.compile(r"^(Chapter\s+[IVXLC0-9]+)\s*[–\-—:]\s*(.+)$", re.I)
ANNEX_RE = re.compile(r"^(Annex(?:ure)?\s+[IVXLC0-9]+)\b(.*)$", re.I)
PART_RE = re.compile(r"^(Part\s+[A-Z0-9IVX]+)\b(.*)$", re.I)
SECTION_RE = re.compile(r"^([A-Z](?:\.\d+){0,3})\s+([A-Z].+)$")
LETTER_HEADING_RE = re.compile(r"^([A-Z])\.\s+([A-Z].+)$")
TOC_LINE_RE = re.compile(r"\.{3,}\s*\d+\s*$")


class HierarchyStack:
    def __init__(self) -> None:
        self.part = None
        self.chapter = None
        self.section = None
        self.subsection = None

    def update_from_line(self, line: str) -> bool:
        s = line.strip()
        if not s:
            return False
        m = PART_RE.match(s)
        if m:
            self.part = " ".join(s.split())
            self.chapter = self.section = self.subsection = None
            return True
        m = CHAPTER_RE.match(s)
        if m:
            self.chapter = f"{m.group(1).strip()} – {m.group(2).strip()}"
            self.section = self.subsection = None
            return True
        m = ANNEX_RE.match(s)
        if m:
            self.chapter = " ".join(s.split())
            self.section = self.subsection = None
            return True
        m = SECTION_RE.match(s)
        if m and len(m.group(2)) < 160 and not m.group(2)[0].isdigit():
            label = m.group(1)
            title = m.group(2).strip()
            if label.count(".") >= 1:
                self.subsection = f"{label} {title}"
                if label.count(".") == 1 and len(label) <= 4:
                    self.section = f"{label} {title}"
                return True
            self.section = f"{label} {title}"
            self.subsection = None
            return True
        m = LETTER_HEADING_RE.match(s)
        if m and len(m.group(2)) < 160:
            self.section = f"{m.group(1)}. {m.group(2).strip()}"
            self.subsection = None
            return True
        return False

    def snapshot(self):
        out = []
        for item in (self.part, self.chapter, self.section, self.subsection):
            if item and item not in out:
                out.append(item)
        return out


def is_hierarchy_line(line: str) -> bool:
    return HierarchyStack().update_from_line(line)


def is_toc_line(line: str) -> bool:
    s = line.strip()
    if TOC_LINE_RE.search(s):
        return True
    if re.search(r"\.{4,}", s) and re.search(r"\d+\s*$", s):
        return True
    return False
