import asyncio
import hashlib
import logging
from typing import List, Dict

from core.llm import get_llm
from langchain_core.prompts import ChatPromptTemplate
from domain.job import JobStage, JobStatus
from ingestion.job_runner import IngestionJobRunner
from db.neo import _driver, neo_store_meeting_knowledge
from db.chroma import vector_store, _embeddings
from integrations.base import KnowledgeDocument
from application.services.teams_service import TeamsService

logger = logging.getLogger(__name__)

from ingestion.pipeline import MeetingExtractionResult, MEETING_PROMPT

class TeamsSyncRunner(IngestionJobRunner):
    def process_teams_sync(self, project_id: str, organization_id: str, user_id: str, provider: str) -> None:
        asyncio.run(self.aprocess_teams_sync(project_id, organization_id, user_id, provider))

    async def aprocess_teams_sync(self, project_id: str, organization_id: str, user_id: str, provider: str) -> None:
        try:
            if not self.job_service.mark_started(self.job_id, self.worker_id, organization_id=self.organization_id):
                return
            self._check_cancelled()
            
            self.job_service.update_progress(self.job_id, stage=JobStage.VALIDATE, progress=0.1)
            
            teams_service = TeamsService()
            access_token = await asyncio.to_thread(teams_service._access_token, project_id)
            documents = await asyncio.to_thread(teams_service.adapter.list_documents, access_token)
            
            self.job_service.update_progress(self.job_id, total_units=len(documents))
            
            meetings_processed = 0
            meetings_failed = 0
            meetings_skipped = 0
            
            for index, document in enumerate(documents):
                self._check_cancelled()
                try:
                    full = await asyncio.to_thread(teams_service.adapter.fetch_document, access_token, document)
                except Exception as exc:
                    meetings_failed += 1
                    logger.error(f"Failed to fetch meeting {document.external_id}: {exc}")
                    continue
                
                transcript_hash = hashlib.sha256(full.text.encode("utf-8")).hexdigest() if full.text.strip() else None
                
                # Deduplication check
                existing = await asyncio.to_thread(self._get_meeting_hash, full.external_id, project_id)
                if transcript_hash and existing == transcript_hash:
                    meetings_skipped += 1
                    continue
                
                try:
                    await self._process_single_meeting(full, project_id, organization_id, transcript_hash, provider)
                    meetings_processed += 1
                except Exception as exc:
                    meetings_failed += 1
                    logger.error(f"Failed to process meeting {full.external_id}: {exc}")
                    await asyncio.to_thread(self._mark_meeting_failed, full.external_id, project_id, organization_id, str(exc))
                
                # Checkpoint progress
                self.job_service.update_progress(
                    self.job_id,
                    completed_units=index + 1,
                    progress=0.1 + 0.8 * ((index + 1) / len(documents)),
                    checkpoint_state={
                        "meetings_processed": meetings_processed,
                        "meetings_skipped": meetings_skipped,
                        "meetings_failed": meetings_failed
                    }
                )

            self.job_service.update_progress(self.job_id, stage=JobStage.FINALIZE, progress=0.99)
            self.job_service.mark_completed(self.job_id)
        except Exception as exc:
            logger.exception(f"Teams sync job {self.job_id} failed: {exc}")
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            if self.job and self.job.status != JobStatus.CANCELLED:
                self.job_service.mark_failed(self.job_id, str(exc))

    def _get_meeting_hash(self, meeting_id: str, project_id: str) -> str:
        with _driver.session() as session:
            existing = session.run("MATCH (m:Meeting {id: $id, project_id: $project_id, organization_id: $organization_id}) WHERE m.processing_state = 'COMPLETED' RETURN m.transcript_hash as transcript_hash", id=meeting_id, project_id=project_id, organization_id=self.job.organization_id).single()
            return existing.get("transcript_hash") if existing else None

    async def _process_single_meeting(self, full: KnowledgeDocument, project_id: str, organization_id: str, transcript_hash: str, provider: str) -> None:
        import time
        await asyncio.to_thread(self._upsert_meeting_node, full, project_id, organization_id, transcript_hash)
        
        if not full.text.strip():
            await asyncio.to_thread(self._mark_meeting_completed, full.external_id, project_id, organization_id, transcript_hash)
            return
            
        max_len = 1000 if provider == "ollama" else 100000
        chunks = self._chunk_text(full.text, max_len)
        
        # We must use self.job.source_id or something similar to remain idempotent.
        # But this is a meeting, so source is full.source
        
        # 1. Embed and store
        chunk_ids = [hashlib.sha256(f"{organization_id}:{project_id}:{full.source}:{i}:{chunk}".encode("utf-8")).hexdigest() for i, chunk in enumerate(chunks)]
        existing_ids = await asyncio.to_thread(vector_store.get_existing_ids, chunk_ids, organization_id, project_id)
        
        missing_chunks = []
        missing_ids = []
        for cid, chunk in zip(chunk_ids, chunks):
            if cid not in existing_ids:
                missing_chunks.append(chunk)
                missing_ids.append(cid)
                
        if missing_chunks:
            embeddings = await asyncio.to_thread(_embeddings.embed_documents, missing_chunks)
            base_metadata = {"source": full.source, "organization_id": organization_id, "project_id": project_id, "document_id": full.external_id, "meeting_id": full.external_id}
            base_metadata.update(full.metadata or {})
            metadatas = [{**base_metadata, "chunk_id": cid, "content_hash": hashlib.sha256(chunk.encode()).hexdigest()} for cid, chunk in zip(missing_ids, missing_chunks)]
            await asyncio.to_thread(vector_store.add_vectors, missing_chunks, embeddings, metadatas, missing_ids)

        # 2. Extract
        llm = get_llm(provider)
        chain = MEETING_PROMPT | llm.with_structured_output(MeetingExtractionResult)
        
        items = []
        for chunk in chunks:
            if not chunk: continue
            self._check_cancelled()
            res = await self._safe_llm_extract_meeting(chain, chunk, provider)
            items.extend(res)
            
        # 3. Store graph
        await asyncio.to_thread(self._write_meeting_knowledge, full.external_id, full.source, project_id, organization_id, items)
        await asyncio.to_thread(self._mark_meeting_completed, full.external_id, project_id, organization_id, transcript_hash)

    async def _safe_llm_extract_meeting(self, chain, chunk: str, provider: str) -> List[Dict]:
        async with self._llm_semaphore:
            max_retries = 3
            backoff = 2
            for attempt in range(max_retries):
                try:
                    self._check_cancelled()
                    response = await chain.ainvoke({"content": chunk})
                    if response and response.items:
                        return [item.model_dump() for item in response.items]
                    return []
                except Exception as exc:
                    exc_str = str(exc).lower()
                    if "429" in exc_str or "rate limit" in exc_str or "timeout" in exc_str or "503" in exc_str:
                        if attempt == max_retries - 1:
                            logger.error(f"Permanent LLM failure on meeting chunk: {exc}")
                            raise
                        logger.warning(f"Transient LLM error, retrying in {backoff}s: {exc}")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                    else:
                        logger.error(f"Non-retriable LLM error: {exc}")
                        raise

    def _upsert_meeting_node(self, full: KnowledgeDocument, project_id: str, organization_id: str, transcript_hash: str) -> None:
        import time
        with _driver.session() as session:
            session.run("""
                MERGE (m:Meeting {id: $id, project_id: $project_id, organization_id: $organization_id})
                SET m.title=$title, m.source=$source, m.start=$start, m.end=$end, m.join_url=$join_url, m.transcript=$transcript, m.processing_state='PROCESSING', m.project_id=$project_id, m.organization_id=$organization_id, m.synced_at=$synced_at
            """, id=full.external_id, project_id=project_id, title=full.title, source=full.source, start=full.metadata.get("start"), end=full.metadata.get("end"), join_url=full.metadata.get("join_url"), transcript=full.text, transcript_hash=transcript_hash, organization_id=organization_id, synced_at=int(time.time()))

    def _mark_meeting_completed(self, meeting_id: str, project_id: str, organization_id: str, transcript_hash: str) -> None:
        with _driver.session() as session:
            session.run("MATCH (m:Meeting {id: $meeting_id, project_id: $project_id, organization_id: $organization_id}) SET m.processing_state='COMPLETED', m.transcript_hash=$transcript_hash", meeting_id=meeting_id, project_id=project_id, organization_id=organization_id, transcript_hash=transcript_hash)

    def _mark_meeting_failed(self, meeting_id: str, project_id: str, organization_id: str, error: str) -> None:
        with _driver.session() as session:
            session.run("MATCH (m:Meeting {id: $meeting_id, project_id: $project_id, organization_id: $organization_id}) SET m.processing_state='FAILED', m.processing_error=$error", meeting_id=meeting_id, project_id=project_id, organization_id=organization_id, error=error)

    def _write_meeting_knowledge(self, meeting_id: str, source: str, project_id: str, organization_id: str, items: List[Dict]) -> None:
        for item in items:
            neo_store_meeting_knowledge(meeting_id=meeting_id, source=source, item=item, project_id=project_id, organization_id=organization_id)
