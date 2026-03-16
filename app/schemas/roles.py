from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class BaseRole(BaseModel):
    id: int
    name: str
    desc: str = ""
    menu_paths: list[str] = Field(default_factory=list)
    api_ids: list[int] = Field(default_factory=list)
    users: Optional[list] = Field(default_factory=list)
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class RoleCreate(BaseModel):
    name: str = Field(..., description="角色名称")
    desc: str = Field("", description="角色描述")
    menu_paths: list[str] = Field(default_factory=list, description="菜单权限路径")
    api_ids: list[int] = Field(default_factory=list, description="API权限ID列表")


class RoleUpdate(BaseModel):
    id: int
    name: Optional[str] = Field(None, description="角色名称")
    desc: Optional[str] = Field(None, description="角色描述")
    menu_paths: Optional[list[str]] = Field(None, description="菜单权限路径")
    api_ids: Optional[list[int]] = Field(None, description="API权限ID列表")
