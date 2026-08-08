-- Tao bang confirmation_progress tren Supabase
CREATE TABLE IF NOT EXISTS confirmation_progress (
    id BIGINT PRIMARY KEY GENERATED ALWAYS AS IDENTITY,
    version_id BIGINT,
    step_order INTEGER,
    team_name TEXT,
    status TEXT DEFAULT 'Waiting',
    comment TEXT,
    action_by TEXT,
    action_at TEXT
);

ALTER TABLE confirmation_progress DISABLE ROW LEVEL SECURITY;
GRANT ALL ON confirmation_progress TO anon, authenticated, service_role;
