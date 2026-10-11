import os
from sqlalchemy import inspect, text
from werkzeug.security import generate_password_hash
from app import app
from backend.database import db
from backend.models import User



ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@marketora.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@12345")




def migrate_roles():
    columns = {c["name"] for c in inspect(db.engine).get_columns("users")}

    if "role" not in columns:
        db.session.execute(text(
            "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'customer'"
        ))
        print("Added users.role column.")

        if "is_admin" in columns:
            db.session.execute(text("UPDATE users SET role='admin' WHERE is_admin = TRUE"))
        if "is_seller" in columns:
            db.session.execute(text(
                "UPDATE users SET role='seller' WHERE is_seller = TRUE AND role = 'customer'"
            ))

    for old in ("is_admin", "is_seller"):
        if old in columns:
            db.session.execute(text(f"ALTER TABLE users DROP COLUMN {old}"))
            print(f"Dropped old users.{old} column.")

    db.session.commit()


def create_admin():
    existing = User.query.filter_by(username=ADMIN_USERNAME).first()
    if existing:
        existing.role = "admin"
        db.session.commit()
        print(f"User '{ADMIN_USERNAME}' already exists - ensured role is admin (password unchanged).")
        return

    admin = User(
        username=ADMIN_USERNAME,
        email=ADMIN_EMAIL,
        password_hash=generate_password_hash(ADMIN_PASSWORD),
        role="admin",
    )
    db.session.add(admin)
    db.session.commit()
    print("Admin created.")
    print(f"  Username: {ADMIN_USERNAME}")
    print(f"  Password: {ADMIN_PASSWORD}")


if __name__ == "__main__":
    with app.app_context():
        migrate_roles()
        create_admin()
