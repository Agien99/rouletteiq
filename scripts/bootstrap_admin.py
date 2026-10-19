import getpass
import os
import sys

from pathlib import Path

from psycopg import errors

# Allow direct execution from the project root.
sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1]),
)

from app.auth_security import hash_password
from app.database import DatabaseConfig
from app.user_repository import UserRepository


def bootstrap_admin() -> None:
    if os.getenv("API_ENV") != "production":
        print(
            "Bootstrap environment: "
            "non-production."
        )

    print("\nRouletteIQ Administrator Setup")
    print("==============================")

    full_name = input("Full name: ").strip()
    email = UserRepository.normalize_email(
        input("Email address: ")
    )

    if not full_name or len(full_name) > 150:
        raise ValueError("Invalid administrator name.")

    password = getpass.getpass("Password: ")
    confirmation = getpass.getpass(
        "Confirm password: "
    )

    if password != confirmation:
        raise ValueError("Passwords do not match.")

    password_hash = hash_password(password)

    with DatabaseConfig.get_connection() as connection:
        with connection.cursor() as cursor:
            # Serialize bootstrap attempts.
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s)",
                (72910411,),
            )

            cursor.execute(
                "SELECT COUNT(*) FROM public.users"
            )

            user_count = cursor.fetchone()[0]

            if user_count != 0:
                raise RuntimeError(
                    "Bootstrap denied: user accounts "
                    "already exist."
                )

            cursor.execute(
                """
                INSERT INTO public.users (
                    full_name,
                    email,
                    password_hash,
                    role,
                    is_active,
                    email_verified_at
                )
                VALUES (
                    %s, %s, %s,
                    'admin', TRUE, NOW()
                )
                RETURNING user_id
                """,
                (
                    full_name,
                    email,
                    password_hash,
                ),
            )

            admin_id = cursor.fetchone()[0]

        connection.commit()

    print("\nAdministrator created successfully.")
    print(f"Administrator ID: {admin_id}")


if __name__ == "__main__":
    try:
        bootstrap_admin()
    except (
        ValueError,
        RuntimeError,
        errors.UniqueViolation,
    ) as exc:
        print(f"\nSetup failed: {exc}")
        sys.exit(1)