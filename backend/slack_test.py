from dotenv import load_dotenv; load_dotenv()
from slack_sdk import WebClient
from core.config import settings

client = WebClient(token=settings.slack_bot_token)
try:
    res = client.conversations_history(channel='C0ARX8F28PQ', limit=5)
    msgs = res['messages']
    print(f"OK — {len(msgs)} messages")
    for m in msgs:
        print(m.get('user'), ':', m.get('text', '')[:80])
except Exception as e:
    print(f"ERROR: {e}")
