import hashlib
import re
from pathlib import Path
from uuid import uuid4

import pymupdf

from app.domain.models import ContentSource, DocumentChunk
from app.infrastructure.content_repository import ContentRepository


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".png", ".jpg", ".jpeg", ".webp"}
MIME_TYPES = {".pdf": "application/pdf", ".txt": "text/plain", ".md": "text/markdown", ".png":"image/png", ".jpg":"image/jpeg", ".jpeg":"image/jpeg", ".webp":"image/webp"}


class DocumentService:
    def __init__(self, repository: ContentRepository, library_root: Path, max_upload_mb: int = 40):
        self.repository = repository
        self.library_root = library_root.resolve()
        self.max_bytes = max_upload_mb * 1024 * 1024

    def ingest(self, campaign_id: str, title: str, source_type: str, visibility: str, file_name: str, data: bytes) -> ContentSource:
        suffix = Path(file_name).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError("Format no admès. Utilitza PDF, TXT, Markdown, PNG, JPG o WebP")
        if not data or len(data) > self.max_bytes:
            raise ValueError(f"El document ha de tenir entre 1 byte i {self.max_bytes // 1024 // 1024} MB")
        checksum = hashlib.sha256(data).hexdigest()
        existing = self.repository.find_by_checksum(campaign_id, checksum)
        if existing:
            raise ValueError(f"Aquest document ja existeix com a '{existing.title}'")
        safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(file_name).stem).strip("._") or "document"
        source_id = f"source_{uuid4().hex[:12]}"
        folder = (self.library_root / campaign_id / source_type).resolve()
        if self.library_root not in folder.parents:
            raise ValueError("Ruta de biblioteca no vàlida")
        folder.mkdir(parents=True, exist_ok=True)
        destination = folder / f"{source_id}_{safe_stem}{suffix}"
        destination.write_bytes(data)
        try:
            pages = self._extract(data, suffix)
            chunks = self._chunk(source_id, pages)
            status = "needs_ocr" if suffix == ".pdf" and sum(len(text) for _, text in pages) < 80 else "ready"
            source = ContentSource(
                id=source_id, campaign_id=campaign_id, title=title.strip() or safe_stem,
                source_type=source_type, file_name=Path(file_name).name,
                file_path=str(destination.relative_to(self.library_root)), mime_type=MIME_TYPES[suffix],
                checksum=checksum, visibility=visibility, page_count=len(pages),
                chunk_count=len(chunks), status=status,
                asset_kind="map" if suffix in {".png", ".jpg", ".jpeg", ".webp"} else "document",
            )
            return self.repository.save(source, chunks)
        except Exception:
            destination.unlink(missing_ok=True)
            raise

    @staticmethod
    def _extract(data: bytes, suffix: str) -> list[tuple[int | None, str]]:
        if suffix == ".pdf":
            with pymupdf.open(stream=data, filetype="pdf") as document:
                return [(index + 1, page.get_text("text").strip()) for index, page in enumerate(document)]
        if suffix in {".txt", ".md"}:
            return [(None, data.decode("utf-8-sig").strip())]
        return []

    @staticmethod
    def _chunk(source_id: str, pages: list[tuple[int | None, str]]) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        for page, text in pages:
            paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
            buffer = ""
            for paragraph in paragraphs:
                if buffer and len(buffer) + len(paragraph) > 1600:
                    chunks.append(DocumentChunk(id=f"chunk_{uuid4().hex[:12]}", source_id=source_id, page=page, text=buffer))
                    buffer = ""
                buffer = f"{buffer}\n\n{paragraph}".strip()
            if buffer:
                chunks.append(DocumentChunk(id=f"chunk_{uuid4().hex[:12]}", source_id=source_id, page=page, text=buffer))
        return chunks

    def delete(self, source_id: str) -> bool:
        source = self.repository.delete(source_id)
        if not source:
            return False
        path = (self.library_root / source.file_path).resolve()
        if self.library_root in path.parents and path.is_file():
            path.unlink()
        return True
