from enum import Enum


class EnumBase(Enum):
    @classmethod
    def get_member_values(cls):
        return [item.value for item in cls._member_map_.values()]

    @classmethod
    def get_member_names(cls):
        return [name for name in cls._member_names_]


class StrEnum(str, Enum):
    """StrEnum implementation compatible with Python 3.10."""
    pass


class MethodType(StrEnum):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"








class DataScope(StrEnum):
    """
    角色数据范围（一期仅 SELF/ALL 生效；DEPARTMENT/ORG 登记预留）

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-09-26 12:50:00  # 北京时间 UTC+8
    """

    SELF = "SELF"
    DEPARTMENT = "DEPARTMENT"
    ORG = "ORG"
    ALL = "ALL"
