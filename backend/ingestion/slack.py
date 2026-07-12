import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from core.config import settings

logger = logging.getLogger(__name__)

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
