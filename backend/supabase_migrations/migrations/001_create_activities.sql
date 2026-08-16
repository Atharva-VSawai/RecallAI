-- Create activities table for storing operational application events
CREATE TABLE IF NOT EXISTS public.activities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    project_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    source TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Indexes to support fast querying and pagination
CREATE INDEX IF NOT EXISTS idx_activities_organization_id ON public.activities(organization_id);
CREATE INDEX IF NOT EXISTS idx_activities_project_id ON public.activities(project_id);
CREATE INDEX IF NOT EXISTS idx_activities_user_id ON public.activities(user_id);
CREATE INDEX IF NOT EXISTS idx_activities_created_at ON public.activities(created_at DESC);

-- Enable Row Level Security (RLS) if required by the application in the future
ALTER TABLE public.activities ENABLE ROW LEVEL SECURITY;

CREATE POLICY activities_read_own_user ON public.activities
    FOR SELECT USING (auth.uid()::text = user_id);
CREATE POLICY activities_insert_own_user ON public.activities
    FOR INSERT WITH CHECK (auth.uid()::text = user_id);
