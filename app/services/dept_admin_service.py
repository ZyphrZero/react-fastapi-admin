from __future__ import annotations

from app.repositories import dept_repository
from app.schemas.depts import DeptCreate, DeptUpdate


class DeptAdminService:
    async def list_dept_tree(self, name: str | None = None) -> list[dict]:
        return await dept_repository.build_tree(name=name)

    async def get_dept_detail(self, dept_id: int) -> dict:
        dept = await dept_repository.get_or_raise(dept_id, "部门不存在")
        return await dept_repository.serialize(dept)

    async def create_dept(self, dept_in: DeptCreate) -> int:
        dept = await dept_repository.create_dept(dept_in)
        return dept.id

    async def update_dept(self, dept_in: DeptUpdate) -> int:
        dept = await dept_repository.update_dept(dept_in)
        return dept.id

    async def delete_dept(self, *, dept_id: int, cascade: bool) -> None:
        await dept_repository.delete_dept(dept_id=dept_id, cascade=cascade)


dept_admin_service = DeptAdminService()
