"""Legacy backend Supabase client scaffold.

Phase 1 freeze marker: current authentication is integrated in the frontend.
Do not use this module for new backend authentication work; replace it during
the planned authentication phase after the architecture is reviewed.
"""

from supabase import create_client
from app.core.config import settings

supabase = create_client(settings.supabase_url, settings.supabase_key)
