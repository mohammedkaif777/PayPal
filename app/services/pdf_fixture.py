from pathlib import Path


def build_simple_pdf(text_lines: list[str]) -> bytes:
    """Build a minimal uncompressed PDF with visible text operators."""
    content_ops: list[str] = []
    y = 720
    for line in text_lines:
        escaped = (
            line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        )
        content_ops.append(f"BT /F1 12 Tf 72 {y} Td ({escaped}) Tj ET")
        y -= 18
    stream = "\n".join(content_ops)
    stream_bytes = stream.encode("latin-1")

    objects = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        (
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        ),
        (
            f"4 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin-1")
            + stream_bytes
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    ]

    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    body = b"".join(objects)
    offsets = [0]
    cursor = len(header)
    for obj in objects:
        offsets.append(cursor)
        cursor += len(obj)

    xref_start = len(header) + len(body)
    xref_lines = ["xref", "0 6", "0000000000 65535 f "]
    for offset in offsets[1:]:
        xref_lines.append(f"{offset:010d} 00000 n ")
    xref = ("\n".join(xref_lines) + "\n").encode("latin-1")
    trailer = (
        f"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n"
    ).encode("latin-1")
    return header + body + xref + trailer


def build_encrypted_pdf_stub() -> bytes:
    """A PDF-looking payload that includes an /Encrypt dictionary marker."""
    return (
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R /Encrypt 9 0 R >>\n"
        b"endobj\n%%EOF\n"
    )


def write_simple_pdf(path: Path, text_lines: list[str]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_simple_pdf(text_lines))
    return path
