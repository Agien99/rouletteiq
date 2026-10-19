from app.database_service import DatabaseService


class UserRepository:
    @staticmethod
    def normalize_email(email: str) -> str:
        normalized = email.strip().lower()

        if not normalized or len(normalized) > 254:
            raise ValueError("Invalid email length.")

        if (
            normalized.count("@") != 1
            or " " in normalized
        ):
            raise ValueError("Invalid email address.")

        return normalized

    @staticmethod
    def get_by_id(user_id: str) -> dict | None:
        return DatabaseService.fetch_one(
            """
            SELECT
                user_id,
                full_name,
                email,
                role,
                is_active,
                email_verified_at,
                created_at,
                updated_at
            FROM public.users
            WHERE user_id = %s
            """,
            (user_id,),
        )

    @staticmethod
    def get_by_email(email: str) -> dict | None:
        normalized = UserRepository.normalize_email(email)

        return DatabaseService.fetch_one(
            """
            SELECT *
            FROM public.users
            WHERE email = %s
            """,
            (normalized,),
        )

    @staticmethod
    def create_user(
        full_name: str,
        email: str,
        password_hash: str | None,
    ) -> dict:
        normalized = UserRepository.normalize_email(email)
        name = full_name.strip()

        if not name or len(name) > 150:
            raise ValueError("Invalid full name.")

        return DatabaseService.execute_returning_one(
            """
            INSERT INTO public.users (
                full_name,
                email,
                password_hash,
                role,
                is_active
            )
            VALUES (%s, %s, %s, 'user', TRUE)
            RETURNING
                user_id,
                full_name,
                email,
                role,
                is_active,
                created_at
            """,
            (
                name,
                normalized,
                password_hash,
            ),
        )

    @staticmethod
    def update_profile(
        user_id: str,
        full_name: str,
    ) -> dict | None:
        name = full_name.strip()

        if not name or len(name) > 150:
            raise ValueError("Invalid full name.")

        return DatabaseService.execute_returning_one(
            """
            UPDATE public.users
            SET full_name = %s,
                updated_at = NOW()
            WHERE user_id = %s
            RETURNING
                user_id,
                full_name,
                email,
                role,
                is_active
            """,
            (name, user_id),
        )

    @staticmethod
    def set_active(
        user_id: str,
        is_active: bool,
    ) -> dict | None:
        return DatabaseService.execute_returning_one(
            """
            UPDATE public.users
            SET is_active = %s,
                updated_at = NOW()
            WHERE user_id = %s
            RETURNING
                user_id,
                email,
                role,
                is_active
            """,
            (is_active, user_id),
        )