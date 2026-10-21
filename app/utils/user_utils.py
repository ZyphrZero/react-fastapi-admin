#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
用户工具类

Author: bixuejun(bxjgood@163.com)
Date: 2025/12/7 21:26
"""

import os
from typing import Optional

from app.controllers.user import user_controller
from app.core.ctx import CTX_USER_ID


class UserUtils:
    def __init__(self):
        pass

    @staticmethod
    async def get_current_user_info() -> Optional[object]:
        """
        获取当前用户信息

        :return: 当前登录用户（contextvar 未设置时返回 None）
        """
        user_id = CTX_USER_ID.get()
        if not user_id:
            return None
        user = await user_controller.get(user_id)
        if not user:
            return None
        return user

    @staticmethod
    def get_file_extension(file_name):
        """
        获取文件扩展名
        :param file_name: 文件名
        :return: 包含点号的扩展名（如 .txt）
        """
        _, extension = os.path.splitext(file_name)
        return extension
