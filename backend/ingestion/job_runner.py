import asyncio
import hashlib
import logging
import time
import uuid
import base64
from typing import List, Dict, Any, Optional

import fitz
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from core.llm import get_llm

from domain.job import IngestionJob, JobStage, JobStatus
from application.services.job_service import JobService
from ingestion.excel import extract_text_from_excel
from ingestion.image import extract_text_from_image
from ingestion.audio import transcribe_audio
from ingestion.document import extract_text_from_document
from db.chroma import vector_store, _embeddings
from application.services.observability_service import breakers, store
from db.neo import neo_store, _driver
from core.config import settings
from infrastructure.repositories.processing_ledger import ProcessingLedger
from infrastructure.repositories.input_store import get_input_store

logger = logging.getLogger(__name__)

# Configurable concurrency, default to 3
import os
INGESTION_LLM_CONCURRENCY = int(os.environ.get("INGESTION_LLM_CONCURRENCY", 3))

PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an organizational memory extractor.
Extract ALL decisions, reasoning, and key information from the content.
Follow the JSON schema perfectly."""),
    ("human", "Content:\n{content}"),
])

class DecisionItem(BaseModel):
    decision: str = Field(description="what was decided")
    reason: str = Field(description="why it was decided")
    impact: str = Field(description="effect on the organization")
    alternatives: List[str] = Field(default_factory=list)
    people: List[str] = Field(default_factory=list)
    timestamp: Optional[str] = Field(default=None)
    topic: str = Field(description="high-level domain")

class ExtractionResult(BaseModel):
    items: List[DecisionItem]

class IngestionJobRunner:
    def __init__(self, job_id: str, job_service: JobService, organization_id: str | None = None):
        self.job_id = job_id
        self.job_service = job_service
        self.organization_id = organization_id
        if organization_id:
            try:
                self.job = self.job_service.get_job(self.job_id, organization_id)
            except TypeError:
                self.job = self.job_service.get_job(self.job_id)
        else:
            self.job = None
        self.worker_id = str(uuid.uuid4())
        self._cancel_check_interval = 10
        self._llm_semaphore = asyncio.Semaphore(INGESTION_LLM_CONCURRENCY)

    def _check_cancelled(self):
        """Raises an exception if the job was cancelled."""
        self.job = self.job_service.get_job(self.job_id, self.organization_id)
        if not self.job:
            raise Exception("Job was deleted while processing.")
        if self.job and self.job.status == JobStatus.CANCELLED:
            raise Exception("Job was cancelled by the user.")

    def _generate_chunk_id(self, chunk_text: str, chunk_index: int) -> str:
        """Deterministic chunk identity."""
        ctx = f"{self.job.organization_id}:{self.job.project_id}:{self.job.source_id}:{chunk_index}:{chunk_text}"
        return hashlib.sha256(ctx.encode("utf-8")).hexdigest()

    async def _safe_llm_extract(self, chain, chunk: str, provider: str) -> List[Dict]:
        """Call LLM with concurrency bounds and transient error backoff."""
        async with self._llm_semaphore:
            max_retries = 3
            backoff = 2
            for attempt in range(max_retries):
                try:
                    self._check_cancelled()
                    response = await chain.ainvoke({"content": chunk})
                    if response and response.items:
                        return [item.model_dump() for item in response.items if item.decision.strip()]
                    return []
                except Exception as exc:
                    exc_str = str(exc).lower()
                    if "429" in exc_str or "rate limit" in exc_str or "timeout" in exc_str or "503" in exc_str:
                        if attempt == max_retries - 1:
                            logger.error(f"Permanent LLM failure on chunk: {exc}")
                            raise
                        logger.warning(f"Transient LLM error, retrying in {backoff}s: {exc}")
                        await asyncio.sleep(backoff)
                        backoff *= 2
                    else:
                        logger.error(f"Non-retriable LLM error: {exc}")
                        raise

    def process_file_bytes(self, file_bytes: Optional[bytes] = None, filename: Optional[str] = None, provider: str = "groq", store_graph: bool = True, store_vector: bool = True) -> None:
        """Process file via asynchronous pipeline."""
        asyncio.run(self.aprocess_file_bytes(file_bytes, filename, provider, store_graph, store_vector))

    async def aprocess_file_bytes(self, file_bytes: Optional[bytes] = None, filename: Optional[str] = None, provider: str = "groq", store_graph: bool = True, store_vector: bool = True) -> None:
        try:
            if not self.job_service.mark_started(self.job_id, self.worker_id, organization_id=self.organization_id):
                return
            
            # Reload job to get correct version
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            if not self.job:
                return

            self._check_cancelled()

            # 1. Load Bytes if not provided
            if not file_bytes:
                if self.job.input_uri:
                    store = get_input_store()
                    file_bytes = await asyncio.to_thread(store.retrieve, self.job.input_uri)
                elif self.job.input_payload_b64:
                    file_bytes = base64.b64decode(self.job.input_payload_b64)
                else:
                    raise ValueError("No input payload available to process.")
            
            if not filename:
                filename = self.job.input_filename or self.job.source_config.get("filename", "unknown")

            # STAGE: EXTRACT TEXT
            if not self.job_service.update_progress(self.job_id, expected_version=self.job.version, worker_id=self.worker_id, stage=JobStage.EXTRACT_TEXT, progress=0.1):
                return
            
            self.job = self.job_service.get_job(self.job_id, self.organization_id) # Reload after CAS
            raw_text = await asyncio.to_thread(self._extract_text, file_bytes, filename, provider)
            self._check_cancelled()

            # STAGE: CHUNK
            if not self.job_service.update_progress(self.job_id, expected_version=self.job.version, worker_id=self.worker_id, stage=JobStage.CHUNK, progress=0.2):
                return
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            
            max_len = 1000 if provider == "ollama" else 100000
            chunks = self._chunk_text(raw_text, max_len)
            
            if not self.job_service.update_progress(self.job_id, expected_version=self.job.version, worker_id=self.worker_id, total_units=len(chunks)):
                return
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            
            self._check_cancelled()

            if not chunks:
                self.job_service.mark_completed(self.job_id, self.worker_id, self.job.version)
                return

            # STAGE: EMBED & STORE_SEMANTIC_MEMORY
            if store_vector:
                if not self.job_service.update_progress(self.job_id, expected_version=self.job.version, worker_id=self.worker_id, stage=JobStage.EMBED, progress=0.3):
                    return
                self.job = self.job_service.get_job(self.job_id, self.organization_id)
                await self._embed_and_store_idempotent(chunks)
            
            self._check_cancelled()

            # STAGE: EXTRACT STRUCTURED KNOWLEDGE & WRITE GRAPH
            if not self.job_service.update_progress(self.job_id, expected_version=self.job.version, worker_id=self.worker_id, stage=JobStage.EXTRACT_STRUCTURED_KNOWLEDGE, progress=0.5):
                return
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            
            llm = get_llm(provider)
            chain = PROMPT | llm.with_structured_output(ExtractionResult)
            
            completed_count = 0
            for index, chunk in enumerate(chunks):
                chunk_hash = hashlib.sha256(chunk.encode()).hexdigest()
                
                # Check ledger
                if ProcessingLedger.is_chunk_completed(self.job.organization_id, self.job.project_id, self.job_id, index):
                    completed_count += 1
                    continue
                    
                if not ProcessingLedger.mark_chunk_processing(self.job.organization_id, self.job.project_id, self.job_id, index, chunk_hash, self.worker_id):
                    # Skip if someone else is processing it
                    continue
                
                self._check_cancelled()
                try:
                    items = await self._safe_llm_extract(chain, chunk, provider)
                    
                    if store_graph and items:
                        await asyncio.to_thread(self._write_graph, items)
                        
                    ProcessingLedger.mark_chunk_completed(self.job.organization_id, self.job.project_id, self.job_id, index, self.worker_id)
                    completed_count += 1
                except Exception as ex:
                    ProcessingLedger.mark_chunk_failed(self.job.organization_id, self.job.project_id, self.job_id, index, self.worker_id)
                    raise ex
                
                # Checkpoint
                prog = 0.5 + 0.4 * (completed_count / len(chunks))
                if not self.job_service.update_progress(
                    self.job_id, 
                    expected_version=self.job.version,
                    worker_id=self.worker_id,
                    progress=prog,
                    completed_units=completed_count
                ):
                    return # lost lease
                self.job = self.job_service.get_job(self.job_id, self.organization_id)

            # STAGE: FINALIZE
            if not self.job_service.update_progress(self.job_id, expected_version=self.job.version, worker_id=self.worker_id, stage=JobStage.FINALIZE, progress=0.99):
                return
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            
            # Register file in Neo4j File registry
            await asyncio.to_thread(self._register_file, filename, hashlib.sha256(file_bytes).hexdigest())
            
            self.job_service.mark_completed(self.job_id, self.worker_id, self.job.version)

        except Exception as exc:
            logger.exception(f"Job {self.job_id} failed: {exc}")
            # Do not overwrite CANCELLED status
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            if self.job and self.job.status != JobStatus.CANCELLED:
                self.job_service.mark_failed(self.job_id, self.worker_id, self.job.version, str(exc))

    def _extract_text(self, file_bytes: bytes, filename: str, provider: str) -> str:
        file_ext = filename.lower().rsplit(".", 1)[-1]
        if file_ext in {"docx", "txt", "md", "markdown", "rtf", "html", "htm", "csv", "log"}:
            return extract_text_from_document(file_bytes, filename)
        elif file_ext in {"xlsx", "xls"}:
            return extract_text_from_excel(file_bytes, filename)
        elif file_ext == "pdf":
            document = fitz.open(stream=file_bytes, filetype="pdf")
            return "\n".join(page.get_text() for page in document)
        elif file_ext in {"png", "jpg", "jpeg", "gif", "webp"}:
            return extract_text_from_image(file_bytes, filename, provider=provider)
        elif file_ext in {"mp3", "wav", "m4a", "mp4", "mov", "avi", "mkv", "flac", "ogg", "webm", "m4v", "3gp"}:
            return transcribe_audio(file_bytes, filename)
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

    def _chunk_text(self, raw_text: str, max_len: int) -> List[str]:
        chunks, current = [], ""
        for paragraph in raw_text.split("\n"):
            if len(current) + len(paragraph) > max_len and current:
                chunks.append(current.strip())
                current = paragraph + "\n"
            else:
                current += paragraph + "\n"
        if current.strip():
            chunks.append(current.strip())
        return chunks

    async def _embed_and_store_idempotent(self, chunks: List[str]) -> None:
        """Embeds and stores chunks idempotently in ChromaDB."""
        # 1. Generate IDs
        chunk_ids = [self._generate_chunk_id(chunk, i) for i, chunk in enumerate(chunks)]
        
        # 2. Check existing
        existing_ids = await asyncio.to_thread(vector_store.get_existing_ids, chunk_ids, self.job.organization_id, self.job.project_id)
        
        # 3. Filter missing
        missing_chunks = []
        missing_ids = []
        for cid, chunk in zip(chunk_ids, chunks):
            if cid not in existing_ids:
                missing_chunks.append(chunk)
                missing_ids.append(cid)
        
        if not missing_chunks:
            return

        # 4. Embed missing (using thread to avoid blocking)
        embeddings = await asyncio.to_thread(lambda: breakers["cohere"].call(lambda: _embeddings.embed_documents(missing_chunks)))
        store.record_usage("embedding", "cohere", units=sum(len(chunk) for chunk in missing_chunks) // 4)
        
        document_id = self.job.source_id
        base_metadata = {"source": self.job.source_id, "organization_id": self.job.organization_id, "project_id": self.job.project_id, "document_id": document_id}
        
        # 5. Store missing
        metadatas = [{**base_metadata, "chunk_id": cid, "content_hash": hashlib.sha256(chunk.encode()).hexdigest()} for cid, chunk in zip(missing_ids, missing_chunks)]
        await asyncio.to_thread(vector_store.add_vectors, missing_chunks, embeddings, metadatas, missing_ids)

    def _write_graph(self, items: List[Dict]) -> None:
        for item in items:
            neo_store(
                subject=item.get("topic", "general"), action=item.get("decision", ""),
                reason=item.get("reason", ""), source=self.job.source_id, people=item.get("people") or [],
                impact=item.get("impact", ""), alternatives=item.get("alternatives") or [],
                timestamp=str(item.get("timestamp") or ""),
                project_id=self.job.project_id,
                organization_id=self.job.organization_id,
            )

    def _register_file(self, filename: str, file_hash: str) -> None:
        with _driver.session() as session:
            session.run("""
                MERGE (f:File {source: $source, project_id: $project_id, organization_id: $organization_id})
                SET f.filename = $filename,
                    f.hash = $hash,
                    f.document_id = $document_id,
                    f.display_source = $display_source,
                    f.content_hash = $hash,
                    f.deleted_at = null,
                    f.uploaded_at = coalesce(f.uploaded_at, $uploaded_at)
            """,
                source=self.job.source_id,
                project_id=self.job.project_id,
                filename=filename,
                hash=file_hash,
                document_id=self.job.source_config.get("document_id", self.job.source_id),
                display_source=self.job.source_config.get("display_source", self.job.source_id),
                organization_id=self.job.organization_id,
                uploaded_at=int(time.time())
            )
