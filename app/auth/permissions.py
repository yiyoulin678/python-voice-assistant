# permissions.py
from enum import Enum, auto

class UserRole(Enum):
    ADMIN = auto()
    USER = auto()

# 这里先做占位接口，未来可以扩展权限点
def is_admin(role: str) -> bool:
    return role.lower() == "admin"

def can_manage_users(role: str) -> bool:
    # 占位接口
    return is_admin(role)

def can_view_logs(role: str) -> bool:
    # 占位接口
    return is_admin(role)

def can_use_ai(role: str) -> bool:
    # 所有用户都能用
    return True