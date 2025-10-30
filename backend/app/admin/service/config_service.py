#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from backend.app.admin.conf import admin_settings
from backend.app.admin.crud.crud_config import config_dao
from backend.app.admin.model import Config
from backend.app.admin.schema.config import CreateConfigParam, UpdateConfigParam
from backend.common.exception import errors
from backend.common.log import log
from backend.core.conf import settings
from backend.database.db_pg import async_db_session
from backend.database.db_redis import redis_client
from backend.utils.serializers import select_as_dict


class ConfigService:
    @staticmethod
    async def get() -> Config | dict:
        async with async_db_session() as db:
            config = await config_dao.get_one(db)
            return config

    @staticmethod
    async def create(*, obj: CreateConfigParam) -> None:
        async with async_db_session.begin() as db:
            config = await config_dao.get_one(db)
            if config:
                raise errors.ForbiddenError(msg='系统配置已存在')
            await config_dao.create(db, obj)
            # await redis_client.hset(admin_settings.CONFIG_REDIS_KEY, mapping=obj.model_dump())

    @staticmethod
    async def update(*, pk: int, obj: UpdateConfigParam) -> int:
        async with async_db_session.begin() as db:
            count = await config_dao.update(db, pk, obj)
            # await redis_client.hset(admin_settings.CONFIG_REDIS_KEY, mapping=obj.model_dump())
            return count

    @staticmethod
    async def delete(*, pk: list[int]) -> int:
        async with async_db_session.begin() as db:
            configs = await config_dao.get_all(db)
            if len(configs) == 1:
                raise errors.ForbiddenError(msg='系统配置无法彻底删除')
            count = await config_dao.delete(db, pk)
            # await redis_client.delete(admin_settings.CONFIG_REDIS_KEY)
            return count

    @staticmethod
    async def get_merged_settings():
        """
        获取合并后的配置，数据库配置优先于环境变量配置
        注意：不再使用缓存，每次都从数据库获取最新配置，以避免多worker环境下的配置不一致问题
        """
        # 创建一个新的settings副本
        merged_settings = settings
        
        try:
            # 每次都从数据库获取最新配置
            async with async_db_session() as db:
                config = await config_dao.get_one(db)
                if config and hasattr(config, 'settings') and config.settings:
                    # 用数据库配置覆盖环境变量配置
                    for key, value in config.settings.items():
                        if hasattr(merged_settings, key) and value is not None and value != "":
                            setattr(merged_settings, key, value)
        except Exception as e:
            log.error(f"Failed to load config from database: {str(e)}")
        
        return merged_settings


config_service = ConfigService()
