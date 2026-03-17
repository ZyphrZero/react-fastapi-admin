from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MethodType


class BaseApi(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    path: str = Field(..., description="API路径", json_schema_extra={"example": "/api/v1/user/list"})
    summary: str = Field("", description="API简介", json_schema_extra={"example": "查看用户列表"})
    method: MethodType = Field(..., description="API方法", json_schema_extra={"example": "GET"})
    tags: str = Field(..., description="API标签", json_schema_extra={"example": "User"})


class ApiCreate(BaseApi):
    pass


class ApiUpdate(BaseApi):
    id: int
