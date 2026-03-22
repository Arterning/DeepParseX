#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from fastapi import Request, Response
from fastapi.security import HTTPBasicCredentials
from starlette.background import BackgroundTask, BackgroundTasks
import requests
import json
import asyncio
from typing import Dict, Any

from backend.utils.encrypt import SM4Cipher

from backend.app.admin.conf import admin_settings
from backend.app.admin.crud.crud_user import user_dao
from backend.app.admin.model import User
from backend.app.admin.schema.token import GetLoginToken, GetNewToken
from backend.app.admin.schema.user import AuthLoginParam, UpdateUserRoleParam
from backend.app.admin.service.login_log_service import LoginLogService
from backend.app.admin.service.user_service import UserService
from backend.common.enums import LoginLogStatusType
from backend.common.exception import errors
from backend.common.response.response_code import CustomErrorCode
from backend.common.security.jwt import (
    create_access_token,
    create_new_token,
    create_refresh_token,
    get_token,
    jwt_decode,
    password_verify,
    get_hash_password,
)
from backend.core.conf import settings
from backend.database.db_pg import async_db_session
from backend.database.db_redis import redis_client
from backend.utils.timezone import timezone


class AuthService:
    @staticmethod
    async def swagger_login(*, obj: HTTPBasicCredentials) -> tuple[str, User]:
        async with async_db_session.begin() as db:
            current_user = await user_dao.get_by_username(db, obj.username)
            if not current_user:
                raise errors.NotFoundError(msg='用户名或密码有误')
            elif not password_verify(f'{obj.password}{current_user.salt}', current_user.password):
                raise errors.AuthorizationError(msg='用户名或密码有误')
            elif not current_user.status:
                raise errors.AuthorizationError(msg='用户已被锁定, 请联系统管理员')
            access_token = await create_access_token(str(current_user.id), current_user.is_multi_login)
            await user_dao.update_login_time(db, obj.username)
            return access_token.access_token, current_user

    @staticmethod
    async def login(
        *, request: Request, response: Response, obj: AuthLoginParam, background_tasks: BackgroundTasks
    ) -> GetLoginToken:
        async with async_db_session.begin() as db:
            try:
                current_user = await user_dao.get_by_username(db, obj.username)
                if not current_user:
                    raise errors.NotFoundError(msg='用户名或密码有误')
                user_uuid = current_user.uuid
                username = current_user.username
                if not password_verify(obj.password + current_user.salt, current_user.password):
                    raise errors.AuthorizationError(msg='用户名或密码有误')
                elif not current_user.status:
                    raise errors.AuthorizationError(msg='用户已被锁定, 请联系统管理员')
                # captcha_code = await redis_client.get(f'{admin_settings.CAPTCHA_LOGIN_REDIS_PREFIX}:{request.state.ip}')
                # if not captcha_code:
                #     raise errors.AuthorizationError(msg='验证码失效，请重新获取')
                # if captcha_code.lower() != obj.captcha.lower():
                #     raise errors.CustomError(error=CustomErrorCode.CAPTCHA_ERROR)
                current_user_id = current_user.id
                access_token = await create_access_token(str(current_user_id), current_user.is_multi_login)
                refresh_token = await create_refresh_token(str(current_user_id), current_user.is_multi_login)
            except errors.NotFoundError as e:
                raise errors.NotFoundError(msg=e.msg)
            except (errors.AuthorizationError, errors.CustomError) as e:
                task = BackgroundTask(
                    LoginLogService.create,
                    **dict(
                        db=db,
                        request=request,
                        user_uuid=user_uuid,
                        username=username,
                        login_time=timezone.now(),
                        status=LoginLogStatusType.fail.value,
                        msg=e.msg,
                    ),
                )
                raise errors.AuthorizationError(msg=e.msg, background=task)
            except Exception as e:
                raise e
            else:
                background_tasks.add_task(
                    LoginLogService.create,
                    **dict(
                        db=db,
                        request=request,
                        user_uuid=user_uuid,
                        username=username,
                        login_time=timezone.now(),
                        status=LoginLogStatusType.success.value,
                        msg='登录成功',
                    ),
                )
                await redis_client.delete(f'{admin_settings.CAPTCHA_LOGIN_REDIS_PREFIX}:{request.state.ip}')
                await user_dao.update_login_time(db, obj.username)
                response.set_cookie(
                    key=settings.COOKIE_REFRESH_TOKEN_KEY,
                    value=refresh_token.refresh_token,
                    max_age=settings.COOKIE_REFRESH_TOKEN_EXPIRE_SECONDS,
                    expires=timezone.f_utc(refresh_token.refresh_token_expire_time),
                    httponly=True,
                )
                await db.refresh(current_user)
                data = GetLoginToken(
                    access_token=access_token.access_token,
                    access_token_expire_time=access_token.access_token_expire_time,
                    user=current_user,  # type: ignore
                )
                return data

    @staticmethod
    async def new_token(*, request: Request, response: Response) -> GetNewToken:
        refresh_token = request.cookies.get(settings.COOKIE_REFRESH_TOKEN_KEY)
        if not refresh_token:
            raise errors.TokenError(msg='Refresh Token 丢失，请重新登录')
        try:
            user_id = jwt_decode(refresh_token)
        except Exception:
            raise errors.TokenError(msg='Refresh Token 无效')
        if request.user.id != user_id:
            raise errors.TokenError(msg='Refresh Token 无效')
        async with async_db_session() as db:
            current_user = await user_dao.get(db, user_id)
            if not current_user:
                raise errors.NotFoundError(msg='用户名或密码有误')
            elif not current_user.status:
                raise errors.AuthorizationError(msg='用户已被锁定, 请联系统管理员')
            current_token = get_token(request)
            new_token = await create_new_token(
                sub=str(current_user.id),
                token=current_token,
                refresh_token=refresh_token,
                multi_login=current_user.is_multi_login,
            )
            response.set_cookie(
                key=settings.COOKIE_REFRESH_TOKEN_KEY,
                value=new_token.new_refresh_token,
                max_age=settings.COOKIE_REFRESH_TOKEN_EXPIRE_SECONDS,
                expires=timezone.f_utc(new_token.new_refresh_token_expire_time),
                httponly=True,
            )
            data = GetNewToken(
                access_token=new_token.new_access_token,
                access_token_expire_time=new_token.new_access_token_expire_time,
            )
            return data

    @staticmethod
    async def logout(*, request: Request, response: Response) -> None:
        token = get_token(request)
        refresh_token = request.cookies.get(settings.COOKIE_REFRESH_TOKEN_KEY)
        response.delete_cookie(settings.COOKIE_REFRESH_TOKEN_KEY)
        if request.user.is_multi_login:
            key = f'{settings.TOKEN_REDIS_PREFIX}:{request.user.id}:{token}'
            await redis_client.delete(key)
            if refresh_token:
                key = f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{request.user.id}:{refresh_token}'
                await redis_client.delete(key)
        else:
            key_prefix = f'{settings.TOKEN_REDIS_PREFIX}:{request.user.id}:'
            await redis_client.delete_prefix(key_prefix)
            key_prefix = f'{settings.TOKEN_REFRESH_REDIS_PREFIX}:{request.user.id}:'
            await redis_client.delete_prefix(key_prefix)
    
    @staticmethod
    def create_test_user_info() -> dict:
        """
        创建测试用的user_info数据，用于模拟OA平台返回的数据结构
        并使用SM4进行加密返回
        
        :return: 包含原始数据和SM4加密结果的字典
        """
        from backend.utils.encrypt import SM4Cipher
        import json
        
        # 构造符合需求的user_info数据结构
        user_info = {
            'loginName': 'test_user',  # 对应username
            'userName': '测试用户',     # 对应user_fullname
            'id': '10001',            # 对应oa_id
            # 可以添加一些额外的字段使数据更完整
            'email': 'test_user@example.com',
            'phone': '13800138000',
            'department': '技术部',
            'position': '工程师'
        }
        
        # 将user_info转换为JSON字符串
        user_info_json = json.dumps(user_info, ensure_ascii=False)
        
        # 使用SM4进行加密
        # 测试用密钥（16字节 = 32个16进制字符）
        test_key = settings.OA_SM4_KEY
        sm4_cipher = SM4Cipher(test_key)
        encrypted_data = sm4_cipher.encrypt(user_info_json)
        print("encrypted_data", encrypted_data)
        
        # 返回原始数据和加密结果
        return {
            'user_info': user_info,
            'user_info_json': user_info_json,
            'sm4_encrypted': encrypted_data,
            'test_key': test_key
        }

    @staticmethod
    async def third_party_login(*, request: Request, response: Response, ticket: str) -> GetLoginToken:
        """
        第三方登录 - OA平台
        
        :param request: 请求对象
        :param response: 响应对象
        :param ticket: 前端传递的ticket
        :return:
        """
        async with async_db_session.begin() as db:
            try:
                # 调用OA平台接口获取用户信息
                oa_url = f"{settings.OA_API_URL}&ticket={ticket}"
                # 使用线程池执行同步的 HTTP 请求，避免阻塞事件循环
                loop = asyncio.get_running_loop()
                oa_response = await loop.run_in_executor(None, lambda: requests.get(oa_url, timeout=10))
                oa_response.raise_for_status()
                
                
                # 使用SM4解密
                encrypted_data = oa_response.text.strip()
                sm4_cipher = SM4Cipher(settings.OA_SM4_KEY)
                decrypted_json = sm4_cipher.decrypt(encrypted_data)
                
                # 解析JSON数据
                user_info = json.loads(decrypted_json)
                
                # 提取必要信息
                username = user_info.get('userName')
                user_fullname = user_info.get('userName')
                oa_id = user_info.get('id')
                
                if not username:
                    raise errors.AuthorizationError(msg='OA登录失败：无法获取用户名')
                
                # 查找或创建用户
                current_user = await user_dao.get_by_username(db, username)
                if not current_user:
                    # 创建新用户，默认密码123456
                    from backend.app.admin.schema.user import RegisterUserParam
                    
                    register_param = RegisterUserParam(
                        username=username,
                        nickname=user_fullname or username,
                        password='123456',
                        email=f"{username}@example.com",
                        is_superuser=True,
                        phone='',
                    )
                    
                    # 使用社交用户方式创建，不进行密码加密（我们在创建后手动设置）
                    current_user = await user_dao.create(db, register_param, social=True)
                    
                    # 重新获取创建的用户
                    # current_user = await user_dao.get_by_username(db, username)
                    
                    # 手动设置密码（包含salt）
                    if current_user:
                        # 生成salt并设置密码
                        from fast_captcha import text_captcha
                        salt = text_captcha(5)
                        current_user.salt = salt
                        current_user.password = get_hash_password(f'123456{salt}')
                        current_user.is_staff = True
                
                # 验证用户状态
                if not current_user.status:
                    raise errors.AuthorizationError(msg='用户已被锁定, 请联系统管理员')
                
                # 生成token
                access_token = await create_access_token(str(current_user.id), current_user.is_multi_login)
                refresh_token = await create_refresh_token(str(current_user.id), current_user.is_multi_login)
                
                # 更新登录时间
                await user_dao.update_login_time(db, username)
                
                # 记录登录日志
                background_tasks = BackgroundTasks()
                background_tasks.add_task(
                    LoginLogService.create,
                    **dict(
                        db=db,
                        request=request,
                        user_uuid=current_user.uuid,
                        username=username,
                        login_time=timezone.now(),
                        status=LoginLogStatusType.success.value,
                        msg='OA登录成功',
                    ),
                )
                
                # 设置cookie
                response.set_cookie(
                    key=settings.COOKIE_REFRESH_TOKEN_KEY,
                    value=refresh_token.refresh_token,
                    max_age=settings.COOKIE_REFRESH_TOKEN_EXPIRE_SECONDS,
                    expires=timezone.f_utc(refresh_token.refresh_token_expire_time),
                    httponly=True,
                )
                
                
            except requests.RequestException as e:
                raise errors.AuthorizationError(msg=f'OA登录失败：无法连接OA服务器，{str(e)}')
            except json.JSONDecodeError:
                raise errors.AuthorizationError(msg='OA登录失败：返回数据格式错误')
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise errors.AuthorizationError(msg=f'OA登录失败：{str(e)}')
        # 返回token和用户信息
        current_user = await user_dao.get_by_username(db, username)
        obj = UpdateUserRoleParam(roles=[1])
        await UserService.update_roles(request=None, username=username, obj=obj)
        data = GetLoginToken(
            access_token=access_token.access_token,
            access_token_expire_time=access_token.access_token_expire_time,
            user=current_user,  # type: ignore
        )
        return data


auth_service = AuthService()
