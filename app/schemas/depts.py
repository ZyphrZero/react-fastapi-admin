from pydantic import BaseModel, Field


class BaseDept(BaseModel):
    name: str = Field(..., description="部门名称", json_schema_extra={"example": "研发中心"})
    desc: str = Field("", description="备注", json_schema_extra={"example": "研发中心"})
    order: int = Field(0, description="排序")
    parent_id: int = Field(0, description="父部门ID")


class DeptCreate(BaseDept): ...


class DeptUpdate(BaseDept):
    id: int

    def update_dict(self):
        return self.model_dump(exclude_unset=True, exclude={"id"})
