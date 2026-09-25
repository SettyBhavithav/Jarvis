-- ====================================================================
-- JARVIS V2: SUPABASE POSTGRESQL + PGVECTOR MASTER SCHEMA
-- Migration Version: 001_initial_schema.sql
-- ====================================================================

-- 1. Enable Required PostgreSQL Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";

-- 2. USERS & PROFILES
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE,
    full_name TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferred_name TEXT DEFAULT 'Setty',
    communication_style TEXT DEFAULT 'concise_british',
    preferred_voice TEXT DEFAULT 'en-US-GuyNeural',
    preferred_fast_model TEXT DEFAULT 'llama-3.1-70b-versatile',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2b. Supabase Auth ↔ Public Users Synchronization Trigger
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, created_at, updated_at)
  VALUES (
    new.id,
    new.email,
    COALESCE(new.raw_user_meta_data->>'full_name', new.email),
    new.created_at,
    new.created_at
  )
  ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;

  INSERT INTO public.user_profiles (user_id, preferred_name)
  VALUES (
    new.id,
    COALESCE(new.raw_user_meta_data->>'full_name', 'Sir')
  )
  ON CONFLICT (user_id) DO NOTHING;

  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
    DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
    CREATE TRIGGER on_auth_user_created
      AFTER INSERT ON auth.users
      FOR EACH ROW EXECUTE PROCEDURE public.handle_new_user();
  END IF;
END $$;

-- 3. SESSIONS, CONVERSATIONS & MESSAGES
CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL, -- 'voice', 'discord', 'api'
    started_at TIMESTAMPTZ DEFAULT NOW(),
    last_activity_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, last_activity_at DESC);

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    title TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL, -- 'system', 'user', 'assistant', 'tool'
    content TEXT NOT NULL,
    tokens INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

-- 4. LONG-TERM MEMORY & PGVECTOR INDEXING
CREATE TABLE IF NOT EXISTS memories (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'general', -- 'general', 'preference', 'project', 'contact', 'habit', 'procedural'
    embedding vector(384), -- 384-dimensional dense vectors (all-MiniLM-L6-v2)
    importance FLOAT DEFAULT 0.5,
    access_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_accessed_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memories_embedding ON memories USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX IF NOT EXISTS idx_memories_user_cat ON memories(user_id, category);

-- 5. KNOWLEDGE GRAPH RELATIONSHIPS
CREATE TABLE IF NOT EXISTS memory_links (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    source_entity TEXT NOT NULL,
    relationship TEXT NOT NULL, -- 'works_on', 'prefers', 'knows', 'uses', 'scheduled_for'
    target_entity TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_memory_links_entities ON memory_links(user_id, source_entity, relationship);

-- 6. DOCUMENT RAG MEMORY
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    file_path TEXT,
    file_type TEXT,
    summary TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    chunk_text TEXT NOT NULL,
    embedding vector(384),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS idx_doc_chunks_embedding ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 7. TASKS & TASK EVENTS
CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'in_progress', 'completed', 'cancelled'
    priority INT DEFAULT 1,
    due_date TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_tasks_status_user ON tasks(user_id, status, due_date);

CREATE TABLE IF NOT EXISTS task_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL, -- 'created', 'updated', 'completed', 'cancelled'
    payload JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 8. AGENT RUNS, STEPS & TOOL EXECUTIONS
CREATE TABLE IF NOT EXISTS agent_runs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    session_id UUID REFERENCES sessions(id) ON DELETE CASCADE,
    goal TEXT NOT NULL,
    status TEXT NOT NULL, -- 'running', 'completed', 'failed'
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS agent_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE CASCADE,
    step_number INT NOT NULL,
    description TEXT NOT NULL,
    tool_name TEXT,
    tool_arguments JSONB,
    observation TEXT,
    status TEXT NOT NULL, -- 'pending', 'executing', 'verified', 'failed'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS tool_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_run_id UUID REFERENCES agent_runs(id) ON DELETE SET NULL,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    arguments JSONB NOT NULL,
    result TEXT,
    success BOOLEAN NOT NULL,
    execution_time_ms FLOAT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 9. SCHEDULER & NOTIFICATIONS
CREATE TABLE IF NOT EXISTS scheduled_tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL, -- 'reminder', 'daily_summary', 'calendar_check', 'research'
    schedule_cron TEXT,
    target_time TIMESTAMPTZ,
    payload JSONB DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL, -- 'voice', 'discord', 'desktop'
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    delivered BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 10. SECURITY AUDIT LOGS
CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    channel TEXT NOT NULL,
    action TEXT NOT NULL,
    tool_name TEXT,
    arguments_summary TEXT,
    risk_level INT NOT NULL,
    confirmed_by_user BOOLEAN NOT NULL DEFAULT FALSE,
    status TEXT NOT NULL, -- 'success', 'failed', 'denied'
    result_summary TEXT
);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- 11. ROW-LEVEL SECURITY (RLS) POLICIES
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE memories ENABLE ROW LEVEL SECURITY;
ALTER TABLE memory_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE agent_steps ENABLE ROW LEVEL SECURITY;
ALTER TABLE tool_executions ENABLE ROW LEVEL SECURITY;
ALTER TABLE scheduled_tasks ENABLE ROW LEVEL SECURITY;
ALTER TABLE notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

-- Standard User Isolation Policies across all User-Owned Tables
DO $$ 
BEGIN
  -- Users Isolation (User can view/edit their own user record; server service role bypasses RLS)
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_user_record') THEN
    CREATE POLICY users_own_user_record ON users FOR ALL USING (auth.uid() = id);
  END IF;

  -- Profiles & Sessions
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_profiles') THEN
    CREATE POLICY users_own_profiles ON user_profiles FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_sessions') THEN
    CREATE POLICY users_own_sessions ON sessions FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_conversations') THEN
    CREATE POLICY users_own_conversations ON conversations FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_messages') THEN
    CREATE POLICY users_own_messages ON messages FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- Long-term Memory & Knowledge Graph
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_memories') THEN
    CREATE POLICY users_own_memories ON memories FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_memory_links') THEN
    CREATE POLICY users_own_memory_links ON memory_links FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- Documents & Chunks
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_documents') THEN
    CREATE POLICY users_own_documents ON documents FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_document_chunks') THEN
    CREATE POLICY users_own_document_chunks ON document_chunks FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- Tasks & Events
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_tasks') THEN
    CREATE POLICY users_own_tasks ON tasks FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_task_events') THEN
    CREATE POLICY users_own_task_events ON task_events FOR ALL USING (
      auth.uid() = user_id OR
      EXISTS (SELECT 1 FROM tasks WHERE tasks.id = task_events.task_id AND tasks.user_id = auth.uid())
    );
  END IF;

  -- Agent Execution & Tool Runs
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_agent_runs') THEN
    CREATE POLICY users_own_agent_runs ON agent_runs FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_agent_steps') THEN
    CREATE POLICY users_own_agent_steps ON agent_steps FOR ALL USING (
      EXISTS (SELECT 1 FROM agent_runs WHERE agent_runs.id = agent_steps.agent_run_id AND agent_runs.user_id = auth.uid())
    );
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_tool_executions') THEN
    CREATE POLICY users_own_tool_executions ON tool_executions FOR ALL USING (auth.uid() = user_id);
  END IF;

  -- Scheduler, Notifications & Audit Logs
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_scheduled_tasks') THEN
    CREATE POLICY users_own_scheduled_tasks ON scheduled_tasks FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_notifications') THEN
    CREATE POLICY users_own_notifications ON notifications FOR ALL USING (auth.uid() = user_id);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE policyname = 'users_own_audit_logs') THEN
    CREATE POLICY users_own_audit_logs ON audit_logs FOR ALL USING (auth.uid() = user_id);
  END IF;
END $$;


-- 12. Helper RPC for pgvector Similarity Search
CREATE OR REPLACE FUNCTION match_memories (
  query_embedding vector(384),
  match_threshold float,
  match_count int,
  p_user_id uuid DEFAULT NULL
)
RETURNS TABLE (
  id uuid,
  text text,
  category text,
  importance float,
  similarity float,
  created_at timestamptz
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT
    memories.id,
    memories.text,
    memories.category,
    memories.importance,
    1 - (memories.embedding <=> query_embedding) AS similarity,
    memories.created_at
  FROM memories
  WHERE (p_user_id IS NULL OR memories.user_id = p_user_id)
    AND 1 - (memories.embedding <=> query_embedding) > match_threshold
  ORDER BY similarity DESC
  LIMIT match_count;
END;
$$;

-- ====================================================================
-- SYSTEM SEED DATA
-- Seeds the canonical JARVIS system user so FK constraints are satisfied
-- for system-level operations. This is idempotent (ON CONFLICT DO NOTHING).
-- ====================================================================
INSERT INTO public.users (id, email, full_name, created_at, updated_at)
VALUES (
  'a0000000-0000-0000-0000-000000000001',
  'system@jarvis.internal',
  'JARVIS System',
  NOW(),
  NOW()
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.user_profiles (user_id, preferred_name)
VALUES ('a0000000-0000-0000-0000-000000000001', 'JARVIS')
ON CONFLICT (user_id) DO NOTHING;
