"""Create (or promote) an admin or lawyer account. Public sign-up only ever creates `client` accounts.

    python -m app.create_admin --email admin@example.com --name "Site Admin"            (asks for the password, hidden)
    python -m app.create_admin --email someone@example.com --role admin --promote       (turn an existing account into an admin)
"""
from __future__ import annotations

import argparse
import getpass
import sys

from .config import get_app_settings
from .db import Database, migrate
from .schemas import check_email, check_password
from .security import hash_password


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--email", required=True)
    ap.add_argument("--name", default="")
    ap.add_argument("--role", choices=["admin", "lawyer"], default="admin")
    ap.add_argument("--promote", action="store_true", help="change the role of an existing account instead of creating one")
    a = ap.parse_args(argv)
    try:
        email = check_email(a.email)
    except ValueError as e:
        print(e)
        return 2

    db = Database(get_app_settings().database_url, max_size=1)
    db.open()
    try:
        migrate(db)
        existing = db.one("select id, role from app.users where lower(email) = %s", [email])
        if a.promote:
            if not existing:
                print("No account with that email.")
                return 1
            db.run("update app.users set role = %s, updated_at = now() where id = %s", [a.role, existing["id"]])
            print(f"{email} is now a {a.role}.")
            return 0
        if existing:
            print("That email already has an account. Use --promote to change its role.")
            return 1
        if len(a.name.strip()) < 2:
            print("--name is required (at least 2 characters).")
            return 2
        pw = getpass.getpass("Password (hidden): ")
        if pw != getpass.getpass("Repeat password: "):
            print("The passwords do not match.")
            return 2
        try:
            check_password(pw)
            if len(pw) < 8:
                raise ValueError("Password needs at least 8 characters, one uppercase letter, one number and one special character.")
        except ValueError as e:
            print(e)
            return 2
        db.run("insert into app.users (email, name, password_hash, role, accepted_terms_at) values (%s, %s, %s, %s, now())",
               [email, a.name.strip(), hash_password(pw), a.role])
        print(f"Created {a.role} account {email}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
