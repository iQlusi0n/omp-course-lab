#!/usr/bin/env python3
"""Render docs/spec.md as a plain-text, multi-page PDF using only the stdlib.

The PDF is hand-assembled: one content stream per page, Helvetica/Courier from
the standard 14 fonts (no embedding), and a correct xref table.

    python3 tools/make_pdf.py                 # docs/spec.md -> docs/spec.pdf
    python3 tools/make_pdf.py in.md out.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PAGE_W, PAGE_H = 612, 792  # US Letter, points
MARGIN_X, MARGIN_TOP = 54, 60
LINE_H = 13
FONT_SIZE = 10
LINES_PER_PAGE = (PAGE_H - 2 * MARGIN_TOP) // LINE_H  # 51
MAX_COLS = 92

_ASCII_MAP = {"—": "-", "–": "-", "…": "...", "→": "->", "“": '"', "”": '"', "‘": "'", "’": "'", "≥": ">="}


def _ascii(text: str) -> str:
    for k, v in _ASCII_MAP.items():
        text = text.replace(k, v)
    return text.encode("ascii", "replace").decode()


def _escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _wrap(line: str) -> list[str]:
    if len(line) <= MAX_COLS:
        return [line]
    out, cur = [], ""
    for word in line.split(" "):
        if cur and len(cur) + 1 + len(word) > MAX_COLS:
            out.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}" if cur else word
    if cur:
        out.append(cur)
    return out


def _classify(md_lines: list[str]) -> list[tuple[str, str]]:
    """Yield (style, text) where style is 'h1', 'h2', 'mono', or 'body'."""
    styled: list[tuple[str, str]] = []
    in_code = False
    for raw in md_lines:
        line = _ascii(raw.rstrip("\n"))
        if line.startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            styled.append(("mono", line))
            continue
        if line.startswith("# "):
            styled.append(("h1", line[2:]))
        elif line.startswith("## ") or line.startswith("### "):
            styled.append(("h2", line.lstrip("# ")))
        elif line.startswith("|"):
            styled.append(("mono", line))
        else:
            for part in _wrap(line):
                styled.append(("body", part))
    return styled


def _page_stream(lines: list[tuple[str, str]], page_no: int, total: int) -> bytes:
    ops = ["BT", f"{MARGIN_X} {PAGE_H - MARGIN_TOP} Td", f"{LINE_H} TL"]
    for style, text in lines:
        if style == "h1":
            ops.append(f"/F2 16 Tf ({_escape(text)}) Tj T*")
        elif style == "h2":
            ops.append(f"/F2 12 Tf ({_escape(text)}) Tj T*")
        elif style == "mono":
            ops.append(f"/F3 9 Tf ({_escape(text)}) Tj T*")
        else:
            ops.append(f"/F1 {FONT_SIZE} Tf ({_escape(text)}) Tj T*")
    ops.append("ET")
    footer = f"omp-course-lab spec - page {page_no} of {total}"
    ops.append(f"BT /F1 8 Tf {MARGIN_X} 30 Td ({_escape(footer)}) Tj ET")
    return "\n".join(ops).encode("latin-1")


def build_pdf(markdown: str) -> bytes:
    styled = _classify(markdown.splitlines())
    pages = [styled[i : i + LINES_PER_PAGE] for i in range(0, len(styled), LINES_PER_PAGE)]
    if len(pages) < 3:  # the fixture must be multi-page; pad rather than fail
        pages += [[("body", "(intentionally blank)")]] * (3 - len(pages))

    objects: list[bytes] = []  # index i -> object number i+1

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font1 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    font2 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>")
    font3 = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Courier /Encoding /WinAnsiEncoding >>")
    pages_obj_num = len(objects) + 1 + 2 * len(pages)  # reserve: after all page+stream objects
    page_nums = []
    for i, page in enumerate(pages, start=1):
        stream = _page_stream(page, i, len(pages))
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        page_num = add(
            (
                f"<< /Type /Page /Parent {pages_obj_num} 0 R /MediaBox [0 0 {PAGE_W} {PAGE_H}] "
                f"/Resources << /Font << /F1 {font1} 0 R /F2 {font2} 0 R /F3 {font3} 0 R >> >> "
                f"/Contents {content} 0 R >>"
            ).encode()
        )
        page_nums.append(page_num)
    kids = " ".join(f"{n} 0 R" for n in page_nums)
    pages_num = add(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode())
    assert pages_num == pages_obj_num
    catalog = add(f"<< /Type /Catalog /Pages {pages_num} 0 R >>".encode())
    info = add(b"<< /Title (omp-course-lab service specification) /Producer (tools/make_pdf.py) >>")

    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = []
    for num, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{num} 0 obj\n".encode() + body + b"\nendobj\n"
    xref_pos = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root {catalog} 0 R /Info {info} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    ).encode()
    return bytes(out)


def main(argv: list[str]) -> int:
    src = Path(argv[1]) if len(argv) > 1 else ROOT / "docs" / "spec.md"
    dst = Path(argv[2]) if len(argv) > 2 else ROOT / "docs" / "spec.pdf"
    pdf = build_pdf(src.read_text(encoding="utf-8"))
    dst.write_bytes(pdf)
    pages = pdf.count(b"/Type /Page ")
    print(f"wrote {dst} ({len(pdf)} bytes, {pages} pages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
