#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import APIRouter

from backend.app.admin.api.v1.sys.api import router as api_router
from backend.app.admin.api.v1.sys.casbin import router as casbin_router
from backend.app.admin.api.v1.sys.config import router as config_router
from backend.app.admin.api.v1.sys.dept import router as dept_router
from backend.app.admin.api.v1.sys.dict_data import router as dict_data_router
from backend.app.admin.api.v1.sys.dict_type import router as dict_type_router
from backend.app.admin.api.v1.sys.menu import router as menu_router
from backend.app.admin.api.v1.sys.role import router as role_router
from backend.app.admin.api.v1.sys.user import router as user_router
from backend.app.admin.api.v1.sys.doc import router as doc_router
from backend.app.admin.api.v1.sys.upload import router as upload_router
from backend.app.admin.api.v1.sys.chat import router as chat_router
from backend.app.admin.api.v1.sys.org import router as org_router
from backend.app.admin.api.v1.sys.assets import router as assets_router
from backend.app.admin.api.v1.sys.account_pwd import router as account_pwd_router
from backend.app.admin.api.v1.sys.ip_addr import router as ip_addr_router
from backend.app.admin.api.v1.sys.event import router as event_router
from backend.app.admin.api.v1.sys.tag import router as tag_router

router = APIRouter(prefix='/sys')

router.include_router(api_router, prefix='/apis', tags=['系统API'])
router.include_router(casbin_router, prefix='/casbin', tags=['系统Casbin权限'])
router.include_router(config_router, prefix='/configs', tags=['系统配置'])
router.include_router(dept_router, prefix='/depts', tags=['系统部门'])
router.include_router(dict_data_router, prefix='/dict_datas', tags=['系统字典数据'])
router.include_router(dict_type_router, prefix='/dict_types', tags=['系统字典类型'])
router.include_router(menu_router, prefix='/menus', tags=['系统目录'])
router.include_router(role_router, prefix='/roles', tags=['系统角色'])
router.include_router(user_router, prefix='/users', tags=['系统用户'])
router.include_router(doc_router, prefix='/docs', tags=['系统文件'])
router.include_router(upload_router, prefix='/upload', tags=['上传文件'])
router.include_router(chat_router, prefix='/chat', tags=['对话'])
router.include_router(org_router,prefix='/org',tags=['系统组织'])
router.include_router(assets_router,prefix='/asset',tags=['系统资产'])
router.include_router(account_pwd_router,prefix='/account_pwd',tags=['文件用户名密码'])
router.include_router(ip_addr_router,prefix='/ip_addr',tags=['文件ip地址'])
router.include_router(event_router,prefix='/events',tags=['事件'])
router.include_router(tag_router,prefix='/tags',tags=['标签'])