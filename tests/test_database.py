from db.database import DatabaseManager

db = DatabaseManager()

db.create_tables()

result = db.register_user("alice", "123456")

print(result)