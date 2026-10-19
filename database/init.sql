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

COMMIT;