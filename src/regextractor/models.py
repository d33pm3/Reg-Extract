from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SourceSpan(BaseModel):
    block_id: str
    start_char: int
    end_char: int


class PageBlock(BaseModel):
    block_id: str
    pdf_page: Optional[int] = None
    printed_page: Optional[int] = None
    text: str
    heading_context: str = ""
    source_engine: str
    block_type: str = "text"
    text_length: int = 0
    page_sha256: str = ""
    ocr_status: str = "not_required"
    ocr_confidence: Optional[float] = None
    layout_warnings: List[str] = Field(default_factory=list)


class SourceInventoryRecord(BaseModel):
    node_id: str
    display_id: str
    parent_node_id: Optional[str] = None
    node_kind: str
    hierarchy: List[str] = Field(default_factory=list)
    sequence_index: int
    start_span: Optional[SourceSpan] = None
    end_span: Optional[SourceSpan] = None
    physical_pdf_pages: List[int] = Field(default_factory=list)
    printed_pages: List[int] = Field(default_factory=list)
    source_blocks: List[str] = Field(default_factory=list)
    disposition: str
    disposition_reason: Optional[str] = None
    raw_preview: str = ""


class ClauseNode(BaseModel):
    clause_id: str
    node_id: str = ""
    display_id: str = ""
    parent_clause_id: Optional[str] = None
    parent_node_id: Optional[str] = None
    node_kind: str = "main_clause"
    hierarchy: List[str] = Field(default_factory=list)
    sequence_index: int = 0
    raw_clause_text: str
    raw_source_text: str = ""
    applicable_entity: str = "N/A"
    obligation_type: str = "Informational"
    action_required: str = "N/A"
    timeline_sla_penalty: str = "N/A"
    source_pdf_pages: List[int] = Field(default_factory=list)
    physical_pdf_pages: List[int] = Field(default_factory=list)
    printed_page_if_available: Optional[int] = None
    printed_pages: List[int] = Field(default_factory=list)
    source_blocks: List[str] = Field(default_factory=list)
    source_spans: List[SourceSpan] = Field(default_factory=list)
    start_span: Optional[SourceSpan] = None
    end_span: Optional[SourceSpan] = None
    source_excerpt: str = ""
    display_excerpt: str = ""
    raw_text_sha256: str = ""
    raw_source_text_sha256: str = ""
    source_pdf_sha256: str = ""
    validation_flags: List[str] = Field(default_factory=list)
    unresolved: bool = False
    footnote_ids: List[str] = Field(default_factory=list)
    amendment_effective_date: Optional[str] = None

    def model_post_init(self, __context: Any) -> None:
        if not self.raw_source_text:
            object.__setattr__(self, "raw_source_text", self.raw_clause_text)
        if not self.display_id:
            object.__setattr__(self, "display_id", self.clause_id)
        if not self.physical_pdf_pages:
            object.__setattr__(self, "physical_pdf_pages", list(self.source_pdf_pages))
        if not self.raw_source_text_sha256 and self.raw_text_sha256:
            object.__setattr__(self, "raw_source_text_sha256", self.raw_text_sha256)

    def page_label(self) -> str:
        pages = [p for p in (self.physical_pdf_pages or self.source_pdf_pages) if isinstance(p, int)]
        if not pages:
            return "PDF_PAGE_UNRESOLVED"
        if min(pages) == max(pages):
            return str(pages[0])
        return f"{min(pages)}-{max(pages)}"


class IngestManifest(BaseModel):
    source_pdf: str
    source_sha256: str
    layout_engine: str
    fallback_used: bool = False
    total_pdf_pages: int
    block_count: int
    notes: List[str] = Field(default_factory=list)
    page_metrics: List[Dict[str, Any]] = Field(default_factory=list)
    capability_mode: str = "COMPATIBILITY"
    ocr_pages: List[int] = Field(default_factory=list)
    blocked_pages: List[int] = Field(default_factory=list)
    min_text_chars: int = 20


class Reconciliation(BaseModel):
    detected_source_nodes: int = 0
    extracted_nodes: int = 0
    explicitly_unresolved_nodes: int = 0
    approved_nonoperative_artifacts: int = 0
    total_clauses_identified: int
    total_clause_nodes_emitted: int
    unique_clause_ids: int
    duplicate_clause_ids: List[str] = Field(default_factory=list)
    potential_numbering_gaps: List[str] = Field(default_factory=list)
    unresolved_clauses: int
    clauses_without_page_provenance: int
    cross_page_clauses: int
    ocr_validation_flags: int
    hierarchy_anomalies: int
    inventory_equation_holds: bool
    inventory_mismatch_detail: Optional[str] = None


class ValidationCheck(BaseModel):
    check_id: str
    gate: str
    target: str
    status: str
    detail: str = ""
