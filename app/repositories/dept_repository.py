from __future__ import annotations

from collections import defaultdict

from tortoise.expressions import Q
from tortoise.transactions import atomic

from app.core.exceptions import RecordNotFoundError, ValidationError
from app.models.admin import Dept, DeptClosure
from app.repositories.base import BaseRepository
from app.schemas.depts import DeptCreate, DeptUpdate


class DeptRepository(BaseRepository[Dept, DeptCreate, DeptUpdate]):
    def __init__(self) -> None:
        super().__init__(model=Dept)

    async def exists_by_name(self, name: str, *, exclude_id: int | None = None) -> bool:
        query = self.model.filter(name=name)
        if exclude_id is not None:
            query = query.exclude(id=exclude_id)
        return await query.exists()

    async def list_for_tree(self, *, name: str | None = None) -> list[Dept]:
        query = Q()
        if name:
            query &= Q(name__contains=name)
        return await self.model.filter(query).order_by("order", "id")

    async def serialize(self, dept: Dept) -> dict:
        return await dept.to_dict()

    async def list_by_ids(self, dept_ids: list[int] | set[int]) -> list[Dept]:
        if not dept_ids:
            return []
        return await self.model.filter(id__in=list(dept_ids)).all()

    async def build_tree(self, *, name: str | None = None) -> list[dict]:
        dept_objects = await self.list_for_tree(name=name)
        dept_ids = {dept.id for dept in dept_objects}
        children_map: dict[int, list[Dept]] = defaultdict(list)

        for dept in dept_objects:
            children_map[dept.parent_id].append(dept)

        def render(parent_id: int) -> list[dict]:
            return [
                {
                    "id": dept.id,
                    "name": dept.name,
                    "desc": dept.desc,
                    "order": dept.order,
                    "parent_id": dept.parent_id,
                    "children": render(dept.id),
                }
                for dept in children_map.get(parent_id, [])
            ]

        root_ids = [dept.id for dept in dept_objects if dept.parent_id == 0 or dept.parent_id not in dept_ids]
        root_nodes: list[dict] = []
        for root_id in root_ids:
            root = next((dept for dept in dept_objects if dept.id == root_id), None)
            if root is None:
                continue
            root_nodes.append(
                {
                    "id": root.id,
                    "name": root.name,
                    "desc": root.desc,
                    "order": root.order,
                    "parent_id": root.parent_id,
                    "children": render(root.id),
                }
            )

        return root_nodes

    async def collect_descendant_ids(self, dept_id: int) -> list[int]:
        dept_objects = await self.model.all().values("id", "parent_id")
        children_map: dict[int, list[int]] = defaultdict(list)
        for dept in dept_objects:
            children_map[dept["parent_id"]].append(dept["id"])

        stack = [dept_id]
        descendants: list[int] = []
        seen: set[int] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            descendants.append(current)
            stack.extend(children_map.get(current, []))
        return descendants

    async def validate_parent(self, *, dept_id: int | None, parent_id: int) -> None:
        if parent_id == 0:
            return

        if dept_id is not None and dept_id == parent_id:
            raise ValidationError("上级部门不能是自己")

        parent = await self.get(parent_id)
        if parent is None:
            raise RecordNotFoundError("上级部门不存在")

        if dept_id is None:
            return

        descendant_ids = await self.collect_descendant_ids(dept_id)
        if parent_id in descendant_ids:
            raise ValidationError("不能将部门移动到自己的子部门下")

    @atomic()
    async def create_dept(self, payload: DeptCreate) -> Dept:
        if await self.exists_by_name(payload.name):
            raise ValidationError(f"部门名称 '{payload.name}' 已存在")

        await self.validate_parent(dept_id=None, parent_id=payload.parent_id)
        dept = await self.create(payload)
        await self.rebuild_closure_table()
        return dept

    @atomic()
    async def update_dept(self, payload: DeptUpdate) -> Dept:
        dept = await self.get_or_raise(payload.id, "部门不存在")

        if payload.name and await self.exists_by_name(payload.name, exclude_id=payload.id):
            raise ValidationError(f"部门名称 '{payload.name}' 已存在")

        await self.validate_parent(dept_id=payload.id, parent_id=payload.parent_id)

        dept.name = payload.name
        dept.desc = payload.desc
        dept.order = payload.order
        dept.parent_id = payload.parent_id
        await dept.save()
        await self.rebuild_closure_table()
        return dept

    @atomic()
    async def delete_dept(self, *, dept_id: int, cascade: bool) -> None:
        await self.get_or_raise(dept_id, "部门不存在")
        descendant_ids = await self.collect_descendant_ids(dept_id)

        if not cascade and len(descendant_ids) > 1:
            raise ValidationError("该部门下有子部门，请先删除子部门或开启级联删除")

        target_ids = descendant_ids if cascade else [dept_id]
        await self.model.filter(id__in=target_ids).delete()
        await self.rebuild_closure_table()

    async def rebuild_closure_table(self) -> None:
        dept_objects = await self.model.all().order_by("id")
        dept_ids = {dept.id for dept in dept_objects}
        children_map: dict[int, list[Dept]] = defaultdict(list)

        for dept in dept_objects:
            children_map[dept.parent_id].append(dept)

        entries: list[DeptClosure] = []
        visited: set[int] = set()

        def traverse(node: Dept, chain: list[int]) -> None:
            if node.id in chain:
                raise ValidationError("检测到非法的部门层级循环")

            full_chain = [*chain, node.id]
            for index, ancestor_id in enumerate(full_chain):
                entries.append(
                    DeptClosure(
                        ancestor=ancestor_id,
                        descendant=node.id,
                        level=len(full_chain) - index - 1,
                    )
                )

            visited.add(node.id)
            for child in children_map.get(node.id, []):
                traverse(child, full_chain)

        root_nodes = [dept for dept in dept_objects if dept.parent_id == 0 or dept.parent_id not in dept_ids]
        for root in root_nodes:
            traverse(root, [])

        for dept in dept_objects:
            if dept.id not in visited:
                traverse(dept, [])

        await DeptClosure.all().delete()
        if entries:
            await DeptClosure.bulk_create(entries)


dept_repository = DeptRepository()
