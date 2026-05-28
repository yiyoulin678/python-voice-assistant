from db.database import DatabaseManager

db = DatabaseManager()

db.create_tables()

# 注册测试
db.register_user("test_user", "123456")

# 登录测试
result = db.check_login("test_user", "wrong")

print(result)