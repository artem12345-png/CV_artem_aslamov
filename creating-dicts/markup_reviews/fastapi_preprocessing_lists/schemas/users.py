from pydantic import BaseModel, SecretStr


class User(BaseModel):
    username: str
    password_hash: SecretStr
