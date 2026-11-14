-- Staff accounts for the Admission Setu admin.
-- Apply this to admission_setu1. It does not change college rows.

CREATE TABLE IF NOT EXISTS staff (
    id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    email text NOT NULL UNIQUE,
    name text NOT NULL,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'editor')),
    is_active boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS staff_sessions (
    token text PRIMARY KEY,
    staff_id bigint NOT NULL REFERENCES staff (id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL
);

CREATE INDEX IF NOT EXISTS staff_sessions_staff_idx ON staff_sessions (staff_id);
