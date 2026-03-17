from __future__ import annotations

from copy import deepcopy

BASE_MENU_TREE = [
    {
        "id": 1,
        "name": "工作台",
        "path": "/dashboard",
        "icon": "material-symbols:dashboard-outline",
        "order": 0,
        "parent_id": 0,
        "is_hidden": False,
        "component": "/dashboard",
        "keepalive": False,
        "redirect": None,
        "children": [],
    },
]

ADMIN_MENU_TREE = [
    {
        "id": 10,
        "name": "系统管理",
        "path": "/system",
        "icon": "carbon:gui-management",
        "order": 1,
        "parent_id": 0,
        "is_hidden": False,
        "component": "Layout",
        "keepalive": False,
        "redirect": "/system/users",
        "children": [
            {
                "id": 11,
                "name": "用户管理",
                "path": "/system/users",
                "icon": "ph:user-list-bold",
                "order": 1,
                "parent_id": 10,
                "is_hidden": False,
                "component": "/system/users",
                "keepalive": False,
                "redirect": None,
            },
            {
                "id": 12,
                "name": "角色管理",
                "path": "/system/roles",
                "icon": "carbon:user-role",
                "order": 2,
                "parent_id": 10,
                "is_hidden": False,
                "component": "/system/roles",
                "keepalive": False,
                "redirect": None,
            },
            {
                "id": 13,
                "name": "API管理",
                "path": "/system/apis",
                "icon": "ant-design:api-outlined",
                "order": 3,
                "parent_id": 10,
                "is_hidden": False,
                "component": "/system/apis",
                "keepalive": False,
                "redirect": None,
            },
            {
                "id": 15,
                "name": "审计日志",
                "path": "/system/audit",
                "icon": "ph:clipboard-text-bold",
                "order": 4,
                "parent_id": 10,
                "is_hidden": False,
                "component": "/system/audit",
                "keepalive": False,
                "redirect": None,
            },
        ],
    },
]


FULL_MENU_TREE = BASE_MENU_TREE + ADMIN_MENU_TREE


def _build_menu_indexes(menu_tree: list[dict]) -> tuple[set[str], dict[str, list[str]], set[str]]:
    all_paths: set[str] = set()
    descendant_leaf_paths: dict[str, list[str]] = {}
    leaf_paths: set[str] = set()

    def visit(node: dict) -> list[str]:
        path = node["path"]
        all_paths.add(path)
        children = node.get("children") or []

        if not children:
            leaf_paths.add(path)
            descendant_leaf_paths[path] = [path]
            return [path]

        current_leaf_paths: list[str] = []
        for child in children:
            current_leaf_paths.extend(visit(child))
        descendant_leaf_paths[path] = current_leaf_paths
        return current_leaf_paths

    for item in menu_tree:
        visit(item)

    return all_paths, descendant_leaf_paths, leaf_paths


ALL_MENU_PATHS, MENU_DESCENDANT_LEAF_PATHS, ASSIGNABLE_MENU_PATHS = _build_menu_indexes(FULL_MENU_TREE)


DEFAULT_ROLE_MENU_PATHS = {
    "管理员": sorted(ASSIGNABLE_MENU_PATHS),
    "普通用户": ["/dashboard"],
}


def get_assignable_menu_tree() -> list[dict]:
    return deepcopy(FULL_MENU_TREE)


def get_default_role_menu_paths(role_name: str) -> list[str]:
    return list(DEFAULT_ROLE_MENU_PATHS.get(role_name, []))


def find_unknown_menu_paths(menu_paths: list[str]) -> list[str]:
    return sorted({path for path in menu_paths if path not in ALL_MENU_PATHS})


def normalize_menu_paths(menu_paths: list[str]) -> list[str]:
    normalized_paths: set[str] = set()
    for path in menu_paths:
        normalized_paths.update(MENU_DESCENDANT_LEAF_PATHS.get(path, []))
    return sorted(normalized_paths)


def _filter_menu_tree(items: list[dict], allowed_paths: set[str]) -> list[dict]:
    filtered_items: list[dict] = []

    for item in items:
        children = _filter_menu_tree(item.get("children") or [], allowed_paths)
        if item["path"] not in allowed_paths and not children:
            continue

        next_item = deepcopy(item)
        next_item["children"] = children
        if children:
            next_item["redirect"] = children[0]["path"]
        filtered_items.append(next_item)

    return filtered_items


def get_system_menu_tree(*, is_superuser: bool, allowed_menu_paths: set[str] | None = None) -> list[dict]:
    if is_superuser:
        return get_assignable_menu_tree()
    return _filter_menu_tree(FULL_MENU_TREE, set(allowed_menu_paths or set()))
