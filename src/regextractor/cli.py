from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .bootstrap import try_install
from .doctor import assess, print_capability, write_report
from .ingest import ingest_pdf, load_page_map
from .models import ClauseNode
from .parser import parse_document, parse_markdown_and_blocks
from .agent import AgentAdapter, write_agent_contract
from .gates import classify_outcome
from .hashing import config_hash, run_id, write_sha256_manifest
from .paths import package_root, version
from .profiles import clause_ids_for, select_profile
from .reconciliation import reconcile
from .renderer import render_output_md, render_qa_report
from .validation import evaluate_clause, find_clause, material_failed, write_smoke_report


def _write_ast(nodes: List[ClauseNode], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "clause_ast.jsonl").open("w", encoding="utf-8") as fh:
        for n in nodes:
            fh.write(n.model_dump_json() + "\n")
    (out_dir / "clause_ast.json").write_text(
        json.dumps([n.model_dump() for n in nodes], indent=2), encoding="utf-8"
    )


def cmd_ingest(args: argparse.Namespace) -> int:
    pdf = Path(args.source)
    if not pdf.exists():
        print(f"ERROR: PDF not found: {pdf}", file=sys.stderr)
        return 2
    manifest = ingest_pdf(pdf, Path(args.out))
    print(f"ingest engine={manifest.layout_engine} pages={manifest.total_pdf_pages} blocks={manifest.block_count}")
    for note in manifest.notes:
        print(f"  note: {note}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    md = Path(args.markdown).read_text(encoding="utf-8")
    blocks = load_page_map(Path(args.page_map))
    parsed = parse_document(md, blocks)
    nodes = parsed.nodes
    recon = reconcile(nodes, parsed.inventory)
    _write_ast(nodes, out)
    with (out / "source_inventory.jsonl").open("w", encoding="utf-8") as fh:
        for rec in parsed.inventory:
            fh.write(rec.model_dump_json() + "\n")
    (out / "output.md").write_text(render_output_md(nodes), encoding="utf-8")
    (out / "reconciliation.json").write_text(recon.model_dump_json(indent=2), encoding="utf-8")
    print(f"extracted {len(nodes)} clauses; inventory_ok={recon.inventory_equation_holds}")
    return 0 if recon.inventory_equation_holds else 1


def _release_hash() -> str:
    root = package_root()
    manifest = root / "RELEASE_MANIFEST.json"
    if manifest.exists():
        try:
            return json.loads(manifest.read_text(encoding="utf-8")).get("release_hash", "UNMANIFESTED")
        except Exception:
            return "UNMANIFESTED"
    return "UNMANIFESTED"


def cmd_doctor(args: argparse.Namespace) -> int:
    source = Path(args.source) if getattr(args, "source", None) else None
    out = Path(args.out) if getattr(args, "out", None) else package_root() / "work" / "doctor"
    report = assess(source, out)
    write_report(report, out)
    print_capability(report)
    print(f"reason={report['reason']} version={report['regextractor_version']}")
    return 0 if report["capability"] != "BLOCKED" else 2


def cmd_bootstrap(args: argparse.Namespace) -> int:
    result = try_install()
    print(json.dumps(result, indent=2))
    report = assess(None, Path(args.out) if getattr(args, "out", None) else None)
    print_capability(report)
    return 0 if report["capability"] != "BLOCKED" else 2


def run_smoke(pdf: Path, out: Path, clause_ids: List[str], work: Optional[Path] = None) -> int:
    if not pdf.exists():
        print("SMOKE_TEST_STATUS = BLOCKED_SOURCE_PDF_REQUIRED")
        out.mkdir(parents=True, exist_ok=True)
        (out / "smoke_test_report.md").write_text(
            "SMOKE_TEST_STATUS = BLOCKED_SOURCE_PDF_REQUIRED\n", encoding="utf-8"
        )
        return 3
    doctor = assess(pdf, out)
    write_report(doctor, out)
    print(doctor["capability"])
    if doctor["capability"] == "BLOCKED":
        print(f"RUNTIME_DOCTOR = BLOCKED reason={doctor['reason']}")
        return 2
    profile = select_profile(pdf)
    if not clause_ids:
        clause_ids = clause_ids_for(profile)
    work = work or (out / "work")
    ingest_dir = work / "ingest"
    extract_dir = work / "extract"
    manifest = ingest_pdf(pdf, ingest_dir)
    md = (ingest_dir / "raw_source.md").read_text(encoding="utf-8")
    blocks = load_page_map(ingest_dir / "page_map.jsonl")
    parsed = parse_document(md, blocks, source_pdf_sha256=manifest.source_sha256)
    nodes = parsed.nodes
    recon = reconcile(nodes, parsed.inventory)
    _write_ast(nodes, extract_dir)
    with (extract_dir / "source_inventory.jsonl").open("w", encoding="utf-8") as fh:
        for rec in parsed.inventory:
            fh.write(rec.model_dump_json() + "\n")
    with (out / "source_inventory.jsonl").open("w", encoding="utf-8") as fh:
        for rec in parsed.inventory:
            fh.write(rec.model_dump_json() + "\n")
    with (out / "source_evidence.jsonl").open("w", encoding="utf-8") as fh:
        for n in nodes:
            fh.write(n.model_dump_json() + "\n")
    (extract_dir / "output.md").write_text(render_output_md(nodes), encoding="utf-8")
    (extract_dir / "reconciliation.json").write_text(recon.model_dump_json(indent=2), encoding="utf-8")
    if not clause_ids:
        discovered = [n.clause_id for n in nodes if getattr(n, "node_kind", "main_clause") != "footnote"]
        clause_ids = clause_ids_for(profile, discovered)
        if not clause_ids and discovered:
            clause_ids = discovered[: min(5, len(discovered))]
    rows = {}
    node_map = {}
    for cid in clause_ids:
        node = find_clause(nodes, cid)
        node_map[cid] = node
        rows[cid] = evaluate_clause(node, cid, md, blocks)
    write_smoke_report(out, clause_ids, rows, node_map)
    failed = [c for c in clause_ids if material_failed(rows[c])]
    smoke_status = {c: ("FAIL" if c in failed else "PASS") for c in clause_ids}
    smoke_status["overall"] = "FAIL" if failed else "PASS"
    smoke_status["capability"] = doctor["capability"]
    smoke_status["version"] = version()
    smoke_status["release_hash"] = _release_hash()
    smoke_status["profile"] = profile.get("profile_id", "generic")
    (extract_dir / "qa_report.md").write_text(render_qa_report(manifest, recon, smoke_status), encoding="utf-8")
    (out / "qa_report.md").write_text(render_qa_report(manifest, recon, smoke_status), encoding="utf-8")
    for name in ("raw_source.md", "page_map.jsonl", "ingest_manifest.json"):
        src = ingest_dir / name
        if src.exists():
            (out / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    for name in ("clause_ast.jsonl", "clause_ast.json", "output.md", "reconciliation.json", "source_inventory.jsonl"):
        src = extract_dir / name
        if src.exists():
            (out / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    import json as _json
    from .package_writer import write_run_sidecar
    try:
        write_run_sidecar(out, nodes, parsed.inventory, recon, manifest, smoke_status, doctor)
    except Exception:
        (out / "validation_results.json").write_text(_json.dumps({"outcome": smoke_status.get("overall"), "checks": []}, indent=2), encoding="utf-8")
        write_sha256_manifest(out)
    if failed:
        print(f"SMOKE_TEST_STATUS = FAIL clauses={failed}")
        return 1
    print("SMOKE_TEST_STATUS = PASS")
    for c in clause_ids:
        n = node_map[c]
        print(f"  clause {c} pages={n.page_label() if n else 'MISSING'}")
    return 0


def cmd_smoke(args: argparse.Namespace) -> int:
    return run_smoke(Path(args.source), Path(args.out), list(args.clauses or []))


def cmd_run(args: argparse.Namespace) -> int:
    return run_smoke(Path(args.source), Path(args.out), list(args.clauses or []))


def cmd_agent(args: argparse.Namespace) -> int:
    adapter = AgentAdapter(Path(args.out), agent_mode=True)
    purpose = args.purpose or ""
    if args.method == "get_run_status":
        print(json.dumps(adapter.get_run_status(args.run_id, purpose), indent=2))
    elif args.method == "get_source_manifest":
        print(json.dumps(adapter.get_source_manifest(args.run_id, purpose), indent=2))
    elif args.method == "list_source_nodes":
        filters = json.loads(args.filters) if args.filters else {}
        print(json.dumps(adapter.list_source_nodes(args.run_id, filters, purpose), indent=2))
    elif args.method == "get_source_node":
        print(json.dumps(adapter.get_source_node(args.run_id, args.node_id, purpose), indent=2))
    elif args.method == "get_evidence":
        print(json.dumps(adapter.get_evidence(args.run_id, args.node_id, purpose), indent=2))
    elif args.method == "validate_run":
        print(json.dumps(adapter.validate_run(args.run_id, purpose), indent=2))
    else:
        print(json.dumps({"error": "unknown_method", "boundary": adapter.get_run_status(args.run_id).get("boundary")}, indent=2))
        return 2
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="regextractor", description="Deterministic regulatory clause extractor")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("ingest")
    s.add_argument("source")
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_ingest)
    s = sub.add_parser("extract")
    s.add_argument("--markdown", required=True)
    s.add_argument("--page-map", required=True)
    s.add_argument("--out", required=True)
    s.set_defaults(func=cmd_extract)
    s = sub.add_parser("smoke-test")
    s.add_argument("source")
    s.add_argument("--clauses", nargs="+", default=None)
    s.add_argument("--out", required=True)
    s.add_argument("--agent-mode", action="store_true")
    s.set_defaults(func=cmd_smoke)
    s = sub.add_parser("run")
    s.add_argument("source")
    s.add_argument("--out", required=True)
    s.add_argument("--clauses", nargs="+", default=None)
    s.add_argument("--agent-mode", action="store_true")
    s.set_defaults(func=cmd_run)
    s = sub.add_parser("doctor")
    s.add_argument("source", nargs="?")
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_doctor)
    s = sub.add_parser("bootstrap")
    s.add_argument("--out", default=None)
    s.set_defaults(func=cmd_bootstrap)
    s = sub.add_parser("agent")
    s.add_argument("method")
    s.add_argument("--out", required=True)
    s.add_argument("--run-id", required=True)
    s.add_argument("--node-id", default=None)
    s.add_argument("--filters", default=None)
    s.add_argument("--purpose", default="")
    s.set_defaults(func=cmd_agent)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
