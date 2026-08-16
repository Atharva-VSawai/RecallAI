"""Legacy backend Supabase client scaffold.

Phase 1 freeze marker: current authentication is integrated in the frontend.
Do not use this module for new backend authentication work; replace it during
the planned authentication phase after the architecture is reviewed.
"""

try:
    from core.config import settings
    from supabase import create_client
    backend_key = settings.supabase_service_role_key
    if not backend_key or backend_key == "your-supabase-service-role-key-here":
        raise ValueError("Missing SUPABASE_SERVICE_ROLE_KEY. Backend requires service role key for operations.")

    supabase = create_client(settings.supabase_url, backend_key)
except ImportError:
    class MockSupabase:
        def table(self, name): return self
        def insert(self, data): return self
        def select(self, *args): return self
        def eq(self, *args): return self
        def order(self, *args, **kwargs): return self
        def range(self, *args): return self
        def execute(self): 
            class Response:
                data = []
            return Response()
            
    create_client = None
    supabase = MockSupabase()
