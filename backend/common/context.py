#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户上下文管理模块
使用 contextvars 在异步环境中传递当前用户信息
"""
from contextvars import ContextVar
from typing import Optional

from backend.app.admin.schema.user import CurrentUserIns

# 创建一个上下文变量来存储当前用户
_current_user: ContextVar[Optional[CurrentUserIns]] = ContextVar('current_user', default=None)


def set_current_user(user: Optional[CurrentUserIns]) -> None:
    """
    设置当前用户到上下文中

    :param user: 当前用户实例
    """
    _current_user.set(user)


def get_current_user() -> Optional[CurrentUserIns]:
    """
    从上下文中获取当前用户

    :return: 当前用户实例，如果未设置则返回 None
    """
    return _current_user.get()


def clear_current_user() -> None:
    """
    清除当前用户上下文
    """
    _current_user.set(None)
