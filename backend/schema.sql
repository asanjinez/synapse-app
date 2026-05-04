-- Ejecutar en Neon después de activar la extensión pgvector
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    goal_text TEXT NOT NULL,
    deadline DATE,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS roadmap_nodes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    parent_id UUID REFERENCES roadmap_nodes(id),
    status TEXT DEFAULT 'pending',
    target_date DATE,
    mastery_pct FLOAT DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fsrs_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    node_id UUID REFERENCES roadmap_nodes(id) ON DELETE CASCADE,
    stability FLOAT DEFAULT 1.0,
    difficulty FLOAT DEFAULT 0.3,
    retrievability FLOAT DEFAULT 1.0,
    next_review_at TIMESTAMPTZ DEFAULT NOW(),
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    type TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS source_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536)
);

CREATE TABLE IF NOT EXISTS assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    due_date DATE,
    completed_at TIMESTAMPTZ
);

-- Índice para búsqueda semántica
CREATE INDEX IF NOT EXISTS source_chunks_embedding_idx
    ON source_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
