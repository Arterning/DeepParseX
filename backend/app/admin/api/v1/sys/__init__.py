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

from backend.app.admin.api.v1.sys.dashboard import router as dashboard_router
from backend.app.admin.api.v1.sys.doc import router as doc_router
from backend.app.admin.api.v1.sys.upload import router as upload_router
from backend.app.admin.api.v1.sys.chat import router as chat_router
from backend.app.admin.api.v1.sys.entity import router as entity_router
from backend.app.admin.api.v1.sys.org import router as org_router
from backend.app.admin.api.v1.sys.person import router as person_router
from backend.app.admin.api.v1.sys.tag import router as tag_router
from backend.app.admin.api.v1.sys.star_collect import router as star_collect_router
from backend.app.admin.api.v1.sys.mail_box import router as mail_box_router
from backend.app.admin.api.v1.sys.mail_msg import router as mail_msg_router
from backend.app.admin.api.v1.sys.subject_predict_object import router as subject_predict_object_router
from backend.app.admin.api.v1.sys.upload_task import router as upload_task_router


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

router.include_router(dashboard_router, prefix='/dashboard', tags=['首页面板'])
router.include_router(doc_router, prefix='/docs', tags=['文件'])
router.include_router(upload_router, prefix='/upload', tags=['上传文件'])
router.include_router(chat_router, prefix='/chat', tags=['对话'])
router.include_router(entity_router,prefix='/entity',tags=['实体'])
router.include_router(org_router,prefix='/org',tags=['组织'])
router.include_router(person_router,prefix='/person',tags=['人物'])
router.include_router(tag_router,prefix='/tags',tags=['标签'])
router.include_router(star_collect_router, prefix='/star_collect', tags=['收藏'])
router.include_router(mail_box_router,prefix='/mailbox',tags=['邮箱'])
router.include_router(mail_msg_router,prefix='/mailmsg',tags=['邮件'])
router.include_router(subject_predict_object_router,prefix='/spo',tags=['要素提取'])
router.include_router(upload_task_router,prefix='/upload_task',tags=['任务管理'])