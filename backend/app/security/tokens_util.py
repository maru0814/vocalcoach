"""配信停止トークン等のランダムトークン生成（docs/89 §2）。"""
import secrets


def new_unsubscribe_token() -> str:
    """URLセーフな暗号学的乱数トークン（43字。users.unsubscribe_token 用）。"""
    return secrets.token_urlsafe(32)
