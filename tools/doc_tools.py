"""Extrae texto de documentos (PDF, Word .docx, texto plano)."""
import os


def extraer_texto(ruta: str, nombre: str = "") -> str:
    ext = os.path.splitext(nombre or ruta)[1].lower()
    if ext == ".pdf":
        from pypdf import PdfReader

        lector = PdfReader(ruta)
        return "\n".join((p.extract_text() or "") for p in lector.pages)
    if ext == ".docx":
        import docx

        doc = docx.Document(ruta)
        return "\n".join(p.text for p in doc.paragraphs)
    # texto plano u otros
    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
        return f.read()
