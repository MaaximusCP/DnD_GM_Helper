from app.domain.models import ContentSource, DocumentChunk, DocumentSearchResult
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

    def search(self, campaign_id: str, query: str, limit: int = 12) -> list[DocumentSearchResult]:
        terms = [term for term in query.replace("'", " ").split() if len(term) >= 3][:8]
        if not terms:
            return []
        clauses = " OR ".join("LOWER(c.text) LIKE ?" for _ in terms)
        parameters = [campaign_id, *(f"%{term.lower()}%" for term in terms), limit * 3]
        with self.database.connect() as db:
            rows = db.execute(f"""SELECT c.id chunk_id, c.source_id, c.page, c.text, s.title source_title
                                   FROM document_chunks c JOIN content_sources s ON s.id=c.source_id
                                   WHERE s.campaign_id=? AND ({clauses}) LIMIT ?""", parameters).fetchall()
        results = []
        for row in rows:
            lowered = row["text"].lower()
            score = sum(lowered.count(term.lower()) for term in terms)
            excerpt = row["text"][:420] + ("…" if len(row["text"]) > 420 else "")
            results.append(DocumentSearchResult(source_id=row["source_id"], source_title=row["source_title"], chunk_id=row["chunk_id"], page=row["page"], excerpt=excerpt, score=score))
        return sorted(results, key=lambda item: item.score, reverse=True)[:limit]

    def delete(self, source_id: str) -> ContentSource | None:
        source = self.get_source(source_id)
        if not source:
            return None
        with self.database.connect() as db:
            db.execute("DELETE FROM document_chunks WHERE source_id=?", (source_id,))
            db.execute("DELETE FROM content_sources WHERE id=?", (source_id,))
        return source
