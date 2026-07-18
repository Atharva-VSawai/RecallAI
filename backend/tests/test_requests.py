import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from pydantic import ValidationError as PydanticValidationError
from schemas.requests import QueryRequest, SlackIngestRequest
from application.services.ingestion_service import IngestionService
from domain.exceptions import ValidationError


def test_query_schema_strips_question():
    assert QueryRequest(question="  What changed? ").question == "What changed?"


@pytest.mark.parametrize("question", ["", " " * 3, "x" * 2001])
def test_query_schema_rejects_invalid_question(question):
    with pytest.raises(PydanticValidationError):
        QueryRequest(question=question)


@pytest.mark.parametrize("channel", ["", "bad channel", "!invalid"])
def test_slack_schema_rejects_invalid_channel(channel):
    with pytest.raises(PydanticValidationError):
        SlackIngestRequest(channel_id=channel)


def test_ingestion_rejects_unsupported_file_without_storage():
    with pytest.raises(ValidationError):
        IngestionService().ingest_upload(b"text", "unsafe.exe", object(), "groq")
