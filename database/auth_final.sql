-- Additive schema migration. Apply once to an existing auth-enabled database.
BEGIN;
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
COMMIT;
