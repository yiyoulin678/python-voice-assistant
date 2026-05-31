from db.database import DatabaseManager

db = DatabaseManager()

db.create_tables()

# 注册
db.register_user("test_user", "123456")

# 登录
print(db.check_login("test_user", "123456"))

# 保存聊天记录
db.save_history(
    1,
    "你好",
    "你好，我是AI助手"
)

# 获取聊天记录
history = db.get_history(1)

print(history)