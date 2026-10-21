from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DataScope

# 一期允许生效的数据范围（SELF/ALL 两级；DEPARTMENT/ORG 仅枚举登记，过滤逻辑二期启用）
ALLOWED_DATA_SCOPES = (DataScope.SELF.value, DataScope.ALL.value)


class BaseRole(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    desc: str = ""
    menu_paths: list[str] = Field(default_factory=list)
    api_ids: list[int] = Field(default_factory=list)
    data_scope: str = DataScope.SELF.value
    users: Optional[list] = Field(default_factory=list)
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class RoleCreate(BaseModel):
    name: str = Field(..., description="角色名称")
    desc: str = Field("", description="角色描述")
    menu_paths: list[str] = Field(default_factory=list, description="菜单权限路径")
    api_ids: list[int] = Field(default_factory=list, description="API权限ID列表")
    data_scope: str = Field(DataScope.SELF.value, description="数据范围（一期仅 SELF/ALL）")


class RoleUpdate(BaseModel):
    id: int
    name: Optional[str] = Field(None, description="角色名称")
    desc: Optional[str] = Field(None, description="角色描述")
    menu_paths: Optional[list[str]] = Field(None, description="菜单权限路径")
    api_ids: Optional[list[int]] = Field(None, description="API权限ID列表")
    data_scope: Optional[str] = Field(None, description="数据范围（一期仅 SELF/ALL）")
