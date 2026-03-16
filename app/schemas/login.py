from pydantic import BaseModel, Field


class CredentialsSchema(BaseModel):
    username: str = Field(..., description="用户名称", example="admin")
    password: str = Field(..., description="密码", example="123456")


class JWTOut(BaseModel):
    access_token: str
    refresh_token: str
    username: str
    token_type: str = "bearer"  # 令牌类型


class JWTRefreshOut(BaseModel):
    access_token: str
    refresh_token: str
