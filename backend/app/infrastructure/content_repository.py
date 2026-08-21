from app.domain.models import ContentSource, ContentSourceUpdate, DocumentChunk, DocumentSearchResult
from app.infrastructure.database import Database


class ContentRepository:
    def __init__(self, database: Database):
        self.database = database

    def find_by_checksum(self, campaign_id: str, checksum: str) -> ContentSource | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM content_sources WHERE campaign_id=? AND checksum=?", (campaign_id, checksum)).fetchone()
            return ContentSource(**dict(row)) if row else None

    def save(self, source: ContentSource, chunks: list[DocumentChunk]) -> ContentSource:
        with self.database.connect() as db:
            db.execute("""INSERT INTO content_sources(id, campaign_id, title, source_type, file_name,
                       file_path, mime_type, checksum, visibility, page_count, chunk_count, status,
                       created_at, asset_kind) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", (
                source.id, source.campaign_id, source.title, source.source_type, source.file_name,
                source.file_path, source.mime_type, source.checksum, source.visibility,
                source.page_count, len(chunks), source.status, source.created_at, source.asset_kind,
            ))
            db.executemany("INSERT INTO document_chunks VALUES (?, ?, ?, ?, ?)", [
                (chunk.id, chunk.source_id, chunk.page, chunk.section, chunk.text) for chunk in chunks
            ])
        return source.model_copy(update={"chunk_count": len(chunks)})

    def list_sources(self, campaign_id: str) -> list[ContentSource]:
        with self.database.connect() as db:
            return [ContentSource(**dict(row)) for row in db.execute(
                "SELECT * FROM content_sources WHERE campaign_id=? ORDER BY created_at DESC", (campaign_id,)
            )]

    def get_source(self, source_id: str) -> ContentSource | None:
        with self.database.connect() as db:
            row = db.execute("SELECT * FROM content_sources WHERE id=?", (source_id,)).fetchone()
            return ContentSource(**dict(row)) if row else None

    def update_source(self, source_id: str, payload: ContentSourceUpdate) -> ContentSource | None:
        values = payload.model_dump(exclude_none=True)
        if values:
            with self.database.connect() as db:
                assignments = ", ".join(f"{key}=?" for key in values)
                db.execute(f"UPDATE content_sources SET {assignments} WHERE id=?", (*values.values(), source_id))
        return self.get_source(source_id)

    def get_chunk(self, chunk_id: str) -> tuple[DocumentChunk, ContentSource] | None:
        with self.database.connect() as db:
            row = db.execute("""SELECT c.*, s.id source_lookup FROM document_chunks c
                                JOIN content_sources s ON s.id=c.source_id WHERE c.id=?""", (chunk_id,)).fetchone()
        if not row:
            return None
        source = self.get_source(row["source_id"])
        if not source:
            return None
        return DocumentChunk(id=row["id"], source_id=row["source_id"], page=row["page"],
                             section=row["section"], text=row["text"]), source

    def list_chunks(self, source_id: str, offset: int = 0, limit: int = 50) -> list[DocumentChunk]:
        with self.database.connect() as db:
            rows = db.execute("""SELECT * FROM document_chunks WHERE source_id=?
                               ORDER BY COALESCE(page, 0), rowid LIMIT ? OFFSET ?""", (source_id, limit, offset))
            return [DocumentChunk(**dict(row)) for row in rows]

    def search(self, campaign_id: str, query: str, limit: int = 12) -> list[DocumentSearchResult]:
        punctuation = ".,;:!?()[]{}\"'"
        terms = [term.strip(punctuation).lower() for term in query.split() if len(term.strip(punctuation)) >= 2][:8]
        if not terms:
            return []
        clauses = " OR ".join("LOWER(c.text) LIKE ? ESCAPE '\\'" for _ in terms)
        escaped = [term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for term in terms]
        parameters = [campaign_id, *(f"%{term}%" for term in escaped), limit * 4]
        with self.database.connect() as db:
            rows = db.execute(f"""SELECT c.id chunk_id, c.source_id, c.page, c.text, s.title source_title
                                   FROM document_chunks c JOIN content_sources s ON s.id=c.source_id
                                   WHERE s.campaign_id=? AND ({clauses}) LIMIT ?""", parameters).fetchall()
        results = []
        for row in rows:
            lowered = row["text"].lower()
            score = sum(lowered.count(term) for term in terms) + sum(2 for term in terms if term in row["source_title"].lower())
            hits = [lowered.find(term) for term in terms if lowered.find(term) >= 0]
            start = max(0, (min(hits) if hits else 0) - 140)
            end = min(len(row["text"]), start + 520)
            excerpt = ("…" if start else "") + row["text"][start:end].strip() + ("…" if end < len(row["text"]) else "")
            results.append(DocumentSearchResult(source_id=row["source_id"], source_title=row["source_title"],
                chunk_id=row["chunk_id"], page=row["page"], excerpt=excerpt, content=row["text"][:10000], score=score))
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]

    def delete(self, source_id: str) -> ContentSource | None:
        source = self.get_source(source_id)
        if not source:
            return None
        with self.database.connect() as db:
            db.execute("DELETE FROM document_chunks WHERE source_id=?", (source_id,))
            db.execute("DELETE FROM content_sources WHERE id=?", (source_id,))
        return source
