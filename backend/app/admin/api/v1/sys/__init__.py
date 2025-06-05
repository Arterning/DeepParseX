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
from backend.app.admin.api.v1.sys.org import router as org_router
from backend.app.admin.api.v1.sys.person import router as person_router
from backend.app.admin.api.v1.sys.assets import router as assets_router
from backend.app.admin.api.v1.sys.ip_addr import router as ip_addr_router
from backend.app.admin.api.v1.sys.event import router as event_router
from backend.app.admin.api.v1.sys.tag import router as tag_router
from backend.app.admin.api.v1.sys.star_collect import router as star_collect_router
from backend.app.admin.api.v1.sys.mail_box import router as mail_box_router
from backend.app.admin.api.v1.sys.mail_msg import router as mail_msg_router
from backend.app.admin.api.v1.sys.subject import router as subject_router
from backend.app.admin.api.v1.sys.scandal import router as scandal_router
from backend.app.admin.api.v1.sys.news import router as news_router
from backend.app.admin.api.v1.sys.social_account import router as social_account_router
from backend.app.admin.api.v1.sys.social_account_post import router as social_account_post_router


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
router.include_router(org_router,prefix='/org',tags=['组织'])
router.include_router(person_router,prefix='/person',tags=['人物'])
router.include_router(assets_router,prefix='/asset',tags=['资产'])
router.include_router(ip_addr_router,prefix='/ip_addr',tags=['提取ip地址'])
router.include_router(event_router,prefix='/events',tags=['事件'])
router.include_router(tag_router,prefix='/tags',tags=['标签'])
router.include_router(star_collect_router, prefix='/star_collect', tags=['收藏'])
router.include_router(mail_box_router,prefix='/mailbox',tags=['邮箱'])
router.include_router(mail_msg_router,prefix='/mailmsg',tags=['邮件'])
router.include_router(subject_router,prefix='/subject',tags=['议题'])
router.include_router(scandal_router, prefix='/scandal', tags=['黑料库'])
router.include_router(news_router,prefix='/news',tags=['新闻'])
router.include_router(social_account_router,prefix='/social_account',tags=['社交账号'])
router.include_router(social_account_post_router,prefix='/social_post',tags=['社交帖子'])