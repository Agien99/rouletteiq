-- RouletteIQ PostgreSQL initial schema
-- Fresh installation only

BEGIN;

CREATE TABLE IF NOT EXISTS public.sessions (
    session_id UUID PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'NEW',
    initial_spin_count INTEGER NOT NULL DEFAULT 0,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.spins (
    spin_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL
        REFERENCES public.sessions(session_id)
        ON DELETE CASCADE,
    spin_index INTEGER NOT NULL,
    number INTEGER NOT NULL CHECK (number BETWEEN 0 AND 36),
    spin_type VARCHAR(20) NOT NULL,
    spun_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(session_id, spin_index)
);

CREATE TABLE IF NOT EXISTS public.model_versions (
    model_version_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_name VARCHAR(100) NOT NULL,
    version_number INTEGER NOT NULL,
    feature_version VARCHAR(100) NOT NULL,
    training_row_count INTEGER NOT NULL,
    training_session_count INTEGER,
    training_parameters JSONB,
    artifact_path TEXT,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    trained_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(model_name, version_number)
);

CREATE TABLE IF NOT EXISTS public.model_metrics (
    model_metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_version_id UUID NOT NULL
        REFERENCES public.model_versions(model_version_id)
        ON DELETE CASCADE,
    metric_scope VARCHAR(100) NOT NULL,
    metric_name VARCHAR(100) NOT NULL,
    metric_value DOUBLE PRECISION NOT NULL,
    sample_count INTEGER NOT NULL,
    evaluation_type VARCHAR(100) NOT NULL,
    calculated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS public.prediction_runs (
    prediction_run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL
        REFERENCES public.sessions(session_id)
        ON DELETE CASCADE,
    model_version_id UUID
        REFERENCES public.model_versions(model_version_id),
    strategy_key VARCHAR(100) NOT NULL,
    prediction_for_spin_index INTEGER NOT NULL,
    input_spin_count INTEGER NOT NULL,
    recent_window INTEGER,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    actual_spin_id UUID
        REFERENCES public.spins(spin_id)
        ON DELETE SET NULL,
    evaluated_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS public.prediction_items (
    prediction_item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_run_id UUID NOT NULL
        REFERENCES public.prediction_runs(prediction_run_id)
        ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL,
    payload JSONB NOT NULL,
    is_hit BOOLEAN,
    evaluated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_spins_session
    ON public.spins(session_id, spin_index);

CREATE INDEX IF NOT EXISTS idx_prediction_runs_session
    ON public.prediction_runs(session_id, generated_at DESC);

CREATE INDEX IF NOT EXISTS idx_prediction_items_run
    ON public.prediction_items(prediction_run_id);

CREATE INDEX IF NOT EXISTS idx_model_metrics_version
    ON public.model_metrics(model_version_id);

-- ==========================================
-- Phase 11A: Authentication Foundation
-- ==========================================

-- 1. User accounts

CREATE TABLE IF NOT EXISTS public.users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(254) NOT NULL,
    password_hash TEXT,
    role VARCHAR(20) NOT NULL DEFAULT 'user'
        CHECK (role IN ('admin', 'user')),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    email_verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT users_email_not_blank
        CHECK (length(trim(email)) > 0),
    CONSTRAINT users_email_normalized
        CHECK (email = lower(trim(email)))
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_email
    ON public.users(email);


-- 2. Linked authentication providers

CREATE TABLE IF NOT EXISTS public.auth_identities (
    identity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(user_id)
        ON DELETE CASCADE,
    provider VARCHAR(30) NOT NULL
        CHECK (provider IN ('google')),
    provider_subject VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(provider, provider_subject),
    UNIQUE(user_id, provider)
);


-- 3. Login sessions

CREATE TABLE IF NOT EXISTS public.auth_sessions (
    auth_session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(user_id)
        ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_auth_sessions_user
    ON public.auth_sessions(user_id);


-- 4. Private registration invitations

CREATE TABLE IF NOT EXISTS public.user_invitations (
    invitation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(254) NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    invited_by UUID NOT NULL
        REFERENCES public.users(user_id),
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    accepted_by UUID
        REFERENCES public.users(user_id),
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (email = lower(trim(email))),
    CHECK (expires_at > created_at),
    CHECK (
        accepted_at IS NULL
        OR accepted_by IS NOT NULL
    ),
    CHECK (
        NOT (
            accepted_at IS NOT NULL
            AND revoked_at IS NOT NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS idx_invitations_email
    ON public.user_invitations(email);


-- 5. Password reset tokens

CREATE TABLE IF NOT EXISTS public.password_reset_tokens (
    reset_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL
        REFERENCES public.users(user_id)
        ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (expires_at > created_at)
);

CREATE INDEX IF NOT EXISTS idx_password_reset_user
    ON public.password_reset_tokens(user_id);


-- 6. Associate roulette sessions with users
-- Temporarily nullable for legacy integration tests.
-- Must become NOT NULL before public deployment.

ALTER TABLE public.sessions
    ADD COLUMN IF NOT EXISTS user_id UUID
        REFERENCES public.users(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_user
    ON public.sessions(user_id);

CREATE TABLE IF NOT EXISTS public.email_verification_tokens (
 verification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
 user_id UUID NOT NULL REFERENCES public.users(user_id) ON DELETE CASCADE,
 token_hash VARCHAR(64) NOT NULL UNIQUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 expires_at TIMESTAMPTZ NOT NULL,
 used_at TIMESTAMPTZ,
 CHECK (expires_at > created_at)
);
CREATE INDEX IF NOT EXISTS idx_email_verification_user ON public.email_verification_tokens(user_id);

CREATE TABLE IF NOT EXISTS public.google_oauth_states (
 state_hash VARCHAR(64) PRIMARY KEY,
 code_verifier VARCHAR(128) NOT NULL,
 nonce VARCHAR(128) NOT NULL,
 invitation_hash VARCHAR(64),
 expires_at TIMESTAMPTZ NOT NULL,
 used_at TIMESTAMPTZ
);

COMMIT;