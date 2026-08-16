import logging
import asyncio
import time
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from core.config import settings
from domain.job import JobStage, JobStatus
from application.services.job_service import JobService
from ingestion.job_runner import IngestionJobRunner
from db.neo import _driver

_client = WebClient(token=settings.slack_bot_token)


def _resolve_username(user_id: str) -> str:
    try:
        res = _client.users_info(user=user_id)
        return res["user"]["real_name"] or res["user"]["name"]
    except Exception:
        return user_id


def fetch_slack_text(channel_id: str, limit: int = 100) -> str:
    """Fetch messages from Slack channel and return as plain text."""
    try:
        res = _client.conversations_history(channel=channel_id, limit=limit)
    except SlackApiError as e:
        raise ValueError(f"Slack API error: {e.response['error']}")

    messages = res.get("messages", [])
    lines = []
    for msg in reversed(messages):
        if msg.get("type") != "message" or msg.get("subtype"):
            continue
        user = _resolve_username(msg.get("user", "unknown"))
        text = msg.get("text", "").strip()
        ts = msg.get("ts", "")
        if text:
            lines.append(f"[{ts}] {user}: {text}")

    if not lines:
        raise ValueError("No valid messages found in channel")

    logger.info(f"[SLACK] Fetched {len(lines)} messages from {channel_id}")
    return "\n".join(lines)


class SlackIngestionRunner(IngestionJobRunner):
    def __init__(self, job_id, job_service):
        super().__init__(job_id, job_service)
        self._claimed_message_ids = []
    def process_slack_channel(self, channel_id: str, limit: int, provider: str = "groq") -> None:
        asyncio.run(self.aprocess_slack_channel(channel_id, limit, provider))

    async def aprocess_slack_channel(self, channel_id: str, limit: int, provider: str = "groq") -> None:
        try:
            if not self.job_service.mark_started(self.job_id, self.worker_id, organization_id=self.organization_id):
                return
            self._check_cancelled()

            # STAGE: EXTRACT TEXT (Fetch Slack incrementally)
            self.job_service.update_progress(self.job_id, stage=JobStage.EXTRACT_TEXT, progress=0.1)
            
            # 1. Fetch last timestamp from Neo4j
            last_ts = await asyncio.to_thread(self._get_last_sync_ts, channel_id)
            
            # 2. Fetch new messages
            raw_text, latest_ts, message_ids = await asyncio.to_thread(self._fetch_incremental_slack_text, channel_id, last_ts, limit)
            self._claimed_message_ids = message_ids
            self._check_cancelled()

            if not raw_text.strip():
                self.job_service.mark_completed(self.job_id)
                return

            # STAGE: CHUNK
            self.job_service.update_progress(self.job_id, stage=JobStage.CHUNK, progress=0.2)
            max_len = 1000 if provider == "ollama" else 100000
            chunks = self._chunk_text(raw_text, max_len)
            self.job_service.update_progress(self.job_id, total_units=len(chunks))
            self._check_cancelled()

            # STAGE: EMBED
            self.job_service.update_progress(self.job_id, stage=JobStage.EMBED, progress=0.3)
            await self._embed_and_store_idempotent(chunks)
            self._check_cancelled()

            # STAGE: EXTRACT STRUCTURED KNOWLEDGE & WRITE GRAPH
            self.job_service.update_progress(self.job_id, stage=JobStage.EXTRACT_STRUCTURED_KNOWLEDGE, progress=0.5)
            
            checkpoint_state = self.job.checkpoint_state or {}
            completed_chunk_indices = set(checkpoint_state.get("completed_chunks", []))
            
            from core.llm import get_llm
            from ingestion.job_runner import PROMPT, ExtractionResult
            llm = get_llm(provider)
            chain = PROMPT | llm.with_structured_output(ExtractionResult)
            
            for index, chunk in enumerate(chunks):
                if index in completed_chunk_indices:
                    continue
                self._check_cancelled()
                items = await self._safe_llm_extract(chain, chunk, provider)
                if items:
                    await asyncio.to_thread(self._write_graph, items)
                completed_chunk_indices.add(index)
                prog = 0.5 + 0.4 * (len(completed_chunk_indices) / len(chunks))
                self.job_service.update_progress(
                    self.job_id, 
                    progress=prog,
                    completed_units=len(completed_chunk_indices),
                    checkpoint_state={"completed_chunks": list(completed_chunk_indices)}
                )

            # STAGE: FINALIZE
            self.job_service.update_progress(self.job_id, stage=JobStage.FINALIZE, progress=0.99)
            if latest_ts:
                await asyncio.to_thread(self._set_last_sync_ts, channel_id, latest_ts)
            await asyncio.to_thread(self._complete_messages, channel_id, self._claimed_message_ids)
            
            self.job_service.mark_completed(self.job_id)

        except Exception as exc:
            logger.exception(f"Slack job {self.job_id} failed: {exc}")
            self.job = self.job_service.get_job(self.job_id, self.organization_id)
            if self.job and self.job.status != JobStatus.CANCELLED:
                self.job_service.mark_failed(self.job_id, str(exc))
            if self._claimed_message_ids:
                await asyncio.to_thread(self._release_messages, channel_id, self._claimed_message_ids)

    def _get_last_sync_ts(self, channel_id: str) -> str:
        with _driver.session() as session:
            result = session.run(
                "MATCH (s:SlackChannel {channel_id: $channel_id, project_id: $project_id, organization_id: $organization_id}) RETURN s.last_timestamp AS ts",
                channel_id=channel_id, project_id=self.job.project_id, organization_id=self.job.organization_id
            ).single()
            return result["ts"] if result and result["ts"] else None

    def _set_last_sync_ts(self, channel_id: str, ts: str) -> None:
        with _driver.session() as session:
            session.run("""
                MERGE (s:SlackChannel {channel_id: $channel_id, project_id: $project_id, organization_id: $organization_id})
                SET s.last_timestamp = $ts
            """, channel_id=channel_id, project_id=self.job.project_id, ts=ts, organization_id=self.job.organization_id)

    def _fetch_incremental_slack_text(self, channel_id: str, oldest: str, limit: int) -> tuple[str, str, list[str]]:
        lines = []
        has_more = True
        cursor = None
        latest_ts = None
        fetched = 0
        message_ids = []

        while has_more and fetched < limit:
            try:
                res = _client.conversations_history(
                    channel=channel_id, 
                    limit=min(limit - fetched, 100),
                    oldest=oldest,
                    inclusive=False,
                    cursor=cursor
                )
            except SlackApiError as e:
                raise ValueError(f"Slack API error: {e.response['error']}")
            
            messages = res.get("messages", [])
            for msg in messages: # Slack returns newest first, but if oldest is provided, it might return oldest first. Actually 'conversations.history' with oldest returns chronological or reverse chronological depending on 'inclusive'. It returns newest first.
                if msg.get("type") != "message" or msg.get("subtype"):
                    continue
                user = _resolve_username(msg.get("user", "unknown"))
                text = msg.get("text", "").strip()
                ts = msg.get("ts", "")
                if not latest_ts or float(ts) > float(latest_ts):
                    latest_ts = ts
                if text:
                    message_id = f"{channel_id}:{ts}"
                    if not self._claim_message(channel_id, message_id):
                        continue
                    lines.append(f"[{ts}] {user}: {text}")
                    message_ids.append(message_id)
            
            fetched += len(messages)
            has_more = res.get("has_more", False)
            if has_more:
                cursor = res.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                has_more = False

        if not lines:
            return "", latest_ts, message_ids

        lines.reverse() # Slack returns newest first, we want chronological
        logger.info(f"[SLACK] Fetched {len(lines)} new messages from {channel_id}")
        return "\n".join(lines), latest_ts, message_ids

    def _claim_message(self, channel_id: str, message_id: str) -> bool:
        with _driver.session() as session:
            result = session.run(
                """
                MERGE (m:SlackMessage {channel_id: $channel_id, message_id: $message_id, project_id: $project_id, organization_id: $organization_id})
                ON CREATE SET m.status = 'PROCESSING', m.claimed_at = $now, m.claim_job = $job_id
                ON MATCH SET m.status = CASE WHEN m.status = 'FAILED' OR (m.status = 'PROCESSING' AND m.claimed_at < $stale_before) THEN 'PROCESSING' ELSE m.status END,
                              m.claimed_at = CASE WHEN m.status = 'PROCESSING' AND m.claimed_at < $stale_before THEN $now ELSE m.claimed_at END,
                              m.claim_job = CASE WHEN m.status = 'PROCESSING' AND m.claimed_at < $stale_before OR m.status = 'FAILED' THEN $job_id ELSE m.claim_job END
                WITH m
                RETURN m.status = 'PROCESSING' AND m.claim_job = $job_id AS claimed
                """,
                channel_id=channel_id, message_id=message_id, project_id=self.job.project_id,
                organization_id=self.job.organization_id, job_id=self.job_id, now=int(time.time()), stale_before=int(time.time()) - 900,
            ).single()
            return bool(result and result["claimed"])

    def _complete_messages(self, channel_id: str, message_ids: list[str]) -> None:
        with _driver.session() as session:
            session.run("MATCH (m:SlackMessage {channel_id: $channel_id, project_id: $project_id, organization_id: $organization_id}) WHERE m.message_id IN $message_ids AND m.claim_job = $job_id SET m.status='COMPLETED', m.completed_at=$now", channel_id=channel_id, project_id=self.job.project_id, organization_id=self.job.organization_id, message_ids=message_ids, now=int(time.time()), job_id=self.job_id)

    def _release_messages(self, channel_id: str, message_ids: list[str]) -> None:
        with _driver.session() as session:
            session.run("MATCH (m:SlackMessage {channel_id: $channel_id, project_id: $project_id, organization_id: $organization_id}) WHERE m.message_id IN $message_ids AND m.claim_job = $job_id SET m.status='FAILED', m.failed_at=$now", channel_id=channel_id, project_id=self.job.project_id, organization_id=self.job.organization_id, message_ids=message_ids, now=int(time.time()), job_id=self.job_id)
