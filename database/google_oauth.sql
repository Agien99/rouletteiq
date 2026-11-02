BEGIN;
CREATE TABLE IF NOT EXISTS public.google_oauth_states (
 state_hash VARCHAR(64) PRIMARY KEY,
 code_verifier VARCHAR(128) NOT NULL,
 nonce VARCHAR(128) NOT NULL,
 invitation_hash VARCHAR(64),
 expires_at TIMESTAMPTZ NOT NULL,
 used_at TIMESTAMPTZ
);
COMMIT;
