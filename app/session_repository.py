from app.database_service import DatabaseService
from app.session import RouletteSession
from app.api.auth_guard import request_user_id


class SessionRepository:
    @staticmethod
    def create_session(session: RouletteSession) -> dict:
        user_id = request_user_id()
        if user_id:
            query = '''INSERT INTO public.sessions
                (session_id,status,initial_spin_count,started_at,ended_at,updated_at,user_id)
                VALUES (%s,%s,%s,%s,%s,NOW(),%s) RETURNING *'''
            params = (session.session_id, session.status, len(session.initial_spins),
                      session.started_at, session.ended_at, user_id)
        else:
            query = '''INSERT INTO public.sessions
                (session_id,status,initial_spin_count,started_at,ended_at,updated_at)
                VALUES (%s,%s,%s,%s,%s,NOW()) RETURNING *'''
            params = (session.session_id, session.status, len(session.initial_spins),
                      session.started_at, session.ended_at)
        result = DatabaseService.execute_returning_one(query, params)
        if result is None:
            raise RuntimeError('Failed to create session record.')
        return result

    @staticmethod
    def update_session(session: RouletteSession) -> None:
        user_id = request_user_id()
        query = '''UPDATE public.sessions SET status=%s,initial_spin_count=%s,
                   started_at=%s,ended_at=%s,updated_at=NOW() WHERE session_id=%s'''
        params = (session.status, len(session.initial_spins), session.started_at,
                  session.ended_at, session.session_id)
        if user_id:
            query += ' AND user_id=%s'
            params += (user_id,)
        DatabaseService.execute(query, params)

    @staticmethod
    def get_session(session_id: str) -> dict | None:
        user_id = request_user_id()
        query = '''SELECT session_id,status,initial_spin_count,started_at,ended_at,
                   created_at,updated_at FROM public.sessions WHERE session_id=%s'''
        params = (session_id,)
        if user_id:
            query += ' AND user_id=%s'
            params += (user_id,)
        return DatabaseService.fetch_one(query, params)

    @staticmethod
    def get_all_sessions() -> list[dict]:
        user_id = request_user_id()
        query = '''SELECT session_id,status,initial_spin_count,started_at,ended_at,
                   created_at,updated_at FROM public.sessions'''
        params = None
        if user_id:
            query += ' WHERE user_id=%s'
            params = (user_id,)
        query += ' ORDER BY started_at DESC'
        return DatabaseService.fetch_all(query, params)
