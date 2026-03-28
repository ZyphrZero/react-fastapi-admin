from app.core.crud import CRUDBase
from app.models.admin import Role
from app.schemas.roles import RoleCreate, RoleUpdate


class RoleController(CRUDBase[Role, RoleCreate, RoleUpdate]):
    """Role controller providing basic role CRUD operations."""

    def __init__(self):
        super().__init__(model=Role)

    async def is_exist(self, name: str) -> bool:
        return await self.model.filter(name=name).exists()

    async def get_role_with_stats(self, role: Role) -> dict:
        """Return role data enriched with statistics."""
        from app.models.admin import User

        # Fetch the base role data.
        role_data = await role.to_dict()

        # Fetch the number of users through the User model.
        user_count = await User.filter(roles=role.id).count()

        # Attach statistics.
        role_data["user_count"] = user_count

        return role_data


role_controller = RoleController()
