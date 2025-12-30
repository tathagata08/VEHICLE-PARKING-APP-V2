# backend/seed.py
from model import db, User, Admin

def database_seed(app):
    """
    Seed the database with initial admins and users.
    Only inserts if the entries do not already exist.
    """
    with app.app_context():
        # --- Seed Admins ---
        admins = [
            {"aid": "admin1", "password": "admin", "first_name": "Alice", "last_name": "Smith", "age": 35, "mob_no": "9000000001"},
            {"aid": "admin2", "password": "admin", "first_name": "Bob", "last_name": "Johnson", "age": 38, "mob_no": "9000000002"}
        ]

        for a in admins:
            existing_admin = Admin.query.filter_by(aid=a["aid"]).first()
            if not existing_admin:
                admin = Admin(
                    aid=a["aid"],
                    password=a["password"],
                    first_name=a["first_name"],
                    last_name=a["last_name"],
                    age=a["age"],
                    mob_no=a["mob_no"]
                )
                db.session.add(admin)
                print(f"Admin added: {a['aid']}")
        db.session.commit()

        # --- Seed Users with real emails ---
        users_data = [
            {"first_name": "John", "last_name": "Doe", "age": 25, "mob_no": "9000000001", "uid": "u001"},
            {"first_name": "Jane", "last_name": "Smith", "age": 28, "mob_no": "9000000002", "uid": "u002"},
            {"first_name": "Michael", "last_name": "Brown", "age": 30, "mob_no": "9000000003", "uid": "u003"},
            {"first_name": "Emily", "last_name": "Davis", "age": 22, "mob_no": "9000000004", "uid": "u004"},
            {"first_name": "David", "last_name": "Wilson", "age": 27, "mob_no": "9000000005", "uid": "u005"},
            {"first_name": "Sarah", "last_name": "Taylor", "age": 26, "mob_no": "9000000006", "uid": "u006"},
            {"first_name": "Daniel", "last_name": "Anderson", "age": 31, "mob_no": "9000000007", "uid": "u007"},
            {"first_name": "Laura", "last_name": "Thomas", "age": 24, "mob_no": "9000000008", "uid": "u008"},
            {"first_name": "James", "last_name": "Jackson", "age": 29, "mob_no": "9000000009", "uid": "u009"},
            {"first_name": "Olivia", "last_name": "White", "age": 23, "mob_no": "9000000010", "uid": "u010"}
        ]

        for u in users_data:
            existing_user = User.query.filter_by(uid=u["uid"]).first()
            if not existing_user:
                email = f"{u['first_name'].lower()}.{u['last_name'].lower()}@example.com"  
                user = User(
                    uid=u["uid"],
                    password="1234",
                    first_name=u["first_name"],
                    last_name=u["last_name"],
                    age=u["age"],
                    mob_no=u["mob_no"],
                    email=email
                )
                db.session.add(user)
                print(f"User added: {u['uid']} - {email}")
        db.session.commit()

        print("Seeding complete!")

# Run independently
if __name__ == "__main__":
    from app import app
    database_seed(app)
