#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
S3/MinIO 导入服务测试脚本
测试 import_service 的 import_from_s3 方法
"""

import sys
import asyncio
import uuid
from datetime import datetime
from io import BytesIO

sys.path.append('../')

from backend.app.admin.service.import_service import import_service
from backend.core.conf import settings
from backend.utils.oss_client import minio_client
from backend.common.log import log


class S3ImportTestSetup:
    """S3 导入测试环境准备"""

    def __init__(self):
        self.bucket_name = 'test-bucket'
        self.test_prefix = f'test_import_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    def setup_test_bucket(self):
        """创建测试桶"""
        try:
            if not minio_client.bucket_exists(self.bucket_name):
                minio_client.make_bucket(self.bucket_name)
                log.info(f"✅ 创建测试桶: {self.bucket_name}")
            else:
                log.info(f"📦 测试桶已存在: {self.bucket_name}")
        except Exception as e:
            log.error(f"❌ 创建测试桶失败: {str(e)}")
            raise

    def create_test_file(self, filename: str, content: str) -> bytes:
        """创建测试文件内容"""
        return content.encode('utf-8')

    def upload_test_files(self):
        """上传测试文件到 MinIO"""
        test_files = {
            # 单个文件测试
            f'{self.test_prefix}/single_file.txt': '这是一个单独的测试文件',

            # 非递归目录测试（根目录文件）
            f'{self.test_prefix}/non_recursive/file1.txt': '非递归目录 - 文件1',
            f'{self.test_prefix}/non_recursive/file2.txt': '非递归目录 - 文件2',
            f'{self.test_prefix}/non_recursive/file3.md': '# 非递归目录 - Markdown文件',

            # 非递归目录测试（子目录文件，不应被导入）
            f'{self.test_prefix}/non_recursive/subdir/file4.txt': '非递归子目录 - 文件4',

            # 递归目录测试
            f'{self.test_prefix}/recursive/root_file.txt': '递归目录 - 根文件',
            f'{self.test_prefix}/recursive/level1/file_l1.txt': '递归目录 - 一级子目录文件',
            f'{self.test_prefix}/recursive/level1/level2/file_l2.txt': '递归目录 - 二级子目录文件',
            f'{self.test_prefix}/recursive/level1/level2/level3/file_l3.md': '# 递归目录 - 三级子目录 Markdown',
        }

        try:
            for object_key, content in test_files.items():
                file_bytes = self.create_test_file(object_key, content)
                buffer = BytesIO(file_bytes)

                minio_client.put_object(
                    self.bucket_name,
                    object_key,
                    buffer,
                    len(file_bytes),
                    content_type='text/plain'
                )
                log.info(f"✅ 上传测试文件: {object_key}")

            log.info(f"📤 共上传 {len(test_files)} 个测试文件")
            return True

        except Exception as e:
            log.error(f"❌ 上传测试文件失败: {str(e)}")
            raise

    def cleanup_test_files(self):
        """清理测试文件"""
        try:
            # 列出所有测试文件
            objects = minio_client.list_objects(
                self.bucket_name,
                prefix=self.test_prefix,
                recursive=True
            )

            # 删除测试文件
            count = 0
            for obj in objects:
                minio_client.remove_object(self.bucket_name, obj.object_name)
                count += 1

            if count > 0:
                log.info(f"🧹 清理了 {count} 个测试文件")
            else:
                log.info("🧹 没有需要清理的测试文件")

        except Exception as e:
            log.error(f"❌ 清理测试文件失败: {str(e)}")


class S3ImportTests:
    """S3 导入功能测试"""

    def __init__(self, setup: S3ImportTestSetup):
        self.setup = setup
        self.bucket_name = setup.bucket_name
        self.test_prefix = setup.test_prefix

        # 测试用的用户信息（请根据实际情况修改）
        self.test_user_id = 1
        self.test_username = "test_user"
        self.test_dept_id = 1
        self.test_doc_dir_id = None  # 可选，默认为根目录

    async def test_single_file_import(self):
        """测试场景1：单个文件导入"""
        log.info("\n" + "="*60)
        log.info("📝 测试场景1：单个文件导入")
        log.info("="*60)

        object_key = f'{self.test_prefix}/single_file.txt'

        try:
            stats = await import_service.import_from_s3(
                bucket_name=self.bucket_name,
                prefix=object_key,
                access_key=settings.ACCESS_KEY,
                secret_key=settings.SECRET_KEY,
                endpoint_url=settings.MINIO_URL,
                recursive=False,
                doc_dir_id=self.test_doc_dir_id,
                dept_id=self.test_dept_id,
                user_id=self.test_user_id,
                username=self.test_username
            )

            log.info(f"\n📊 导入统计:")
            log.info(f"  ├─ 总数: {stats['total']}")
            log.info(f"  ├─ 成功: {stats['success']}")
            log.info(f"  ├─ 失败: {stats['failed']}")
            log.info(f"  └─ 错误: {stats['errors']}")

            assert stats['total'] == 1, f"预期导入1个文件，实际: {stats['total']}"
            assert stats['success'] == 1, f"预期成功1个，实际: {stats['success']}"

            log.info("✅ 单个文件导入测试通过")
            return stats

        except Exception as e:
            log.error(f"❌ 单个文件导入测试失败: {str(e)}")
            raise

    async def test_non_recursive_directory_import(self):
        """测试场景2：非递归目录导入"""
        log.info("\n" + "="*60)
        log.info("📝 测试场景2：非递归目录导入")
        log.info("="*60)

        prefix = f'{self.test_prefix}/non_recursive/'

        try:
            stats = await import_service.import_from_s3(
                bucket_name=self.bucket_name,
                prefix=prefix,
                access_key=settings.ACCESS_KEY,
                secret_key=settings.SECRET_KEY,
                endpoint_url=settings.MINIO_URL,
                recursive=False,  # 非递归
                doc_dir_id=self.test_doc_dir_id,
                dept_id=self.test_dept_id,
                user_id=self.test_user_id,
                username=self.test_username
            )

            log.info(f"\n📊 导入统计:")
            log.info(f"  ├─ 总数: {stats['total']}")
            log.info(f"  ├─ 成功: {stats['success']}")
            log.info(f"  ├─ 失败: {stats['failed']}")
            log.info(f"  └─ 错误: {stats['errors']}")

            # 预期导入3个文件（file1.txt, file2.txt, file3.md）
            # 不包括子目录中的 file4.txt
            assert stats['total'] == 3, f"预期导入3个文件，实际: {stats['total']}"

            log.info("✅ 非递归目录导入测试通过")
            return stats

        except Exception as e:
            log.error(f"❌ 非递归目录导入测试失败: {str(e)}")
            raise

    async def test_recursive_directory_import(self):
        """测试场景3：递归目录导入"""
        log.info("\n" + "="*60)
        log.info("📝 测试场景3：递归目录导入")
        log.info("="*60)

        prefix = f'{self.test_prefix}/recursive/'

        try:
            stats = await import_service.import_from_s3(
                bucket_name=self.bucket_name,
                prefix=prefix,
                access_key=settings.ACCESS_KEY,
                secret_key=settings.SECRET_KEY,
                endpoint_url=settings.MINIO_URL,
                recursive=True,  # 递归
                doc_dir_id=self.test_doc_dir_id,
                dept_id=self.test_dept_id,
                user_id=self.test_user_id,
                username=self.test_username
            )

            log.info(f"\n📊 导入统计:")
            log.info(f"  ├─ 总数: {stats['total']}")
            log.info(f"  ├─ 成功: {stats['success']}")
            log.info(f"  ├─ 失败: {stats['failed']}")
            log.info(f"  └─ 错误: {stats['errors']}")

            # 预期导入4个文件（包括所有层级的文件）
            assert stats['total'] == 4, f"预期导入4个文件，实际: {stats['total']}"

            log.info("✅ 递归目录导入测试通过")
            return stats

        except Exception as e:
            log.error(f"❌ 递归目录导入测试失败: {str(e)}")
            raise

    async def run_all_tests(self):
        """运行所有测试"""
        log.info("\n" + "🚀"*30)
        log.info("开始运行 S3 导入服务测试")
        log.info("🚀"*30)

        results = {}

        try:
            # 测试1: 单个文件导入
            results['single_file'] = await self.test_single_file_import()
            await asyncio.sleep(1)  # 避免操作过快

            # 测试2: 非递归目录导入
            results['non_recursive'] = await self.test_non_recursive_directory_import()
            await asyncio.sleep(1)

            # 测试3: 递归目录导入
            results['recursive'] = await self.test_recursive_directory_import()

            # 总结
            log.info("\n" + "="*60)
            log.info("📋 测试总结")
            log.info("="*60)

            total_imported = sum(r['success'] for r in results.values())
            total_failed = sum(r['failed'] for r in results.values())

            log.info(f"✅ 所有测试通过!")
            log.info(f"📊 总共导入: {total_imported} 个文件")
            log.info(f"❌ 失败: {total_failed} 个文件")

            for test_name, stats in results.items():
                log.info(f"\n{test_name}:")
                log.info(f"  成功: {stats['success']}, 失败: {stats['failed']}")
                if stats['errors']:
                    log.info(f"  错误信息: {stats['errors']}")

            return results

        except Exception as e:
            log.error(f"\n❌ 测试执行失败: {str(e)}")
            raise


async def main():
    """主测试流程"""
    setup = S3ImportTestSetup()

    try:
        # 1. 准备测试环境
        log.info("📦 步骤1: 准备测试环境")
        setup.setup_test_bucket()
        setup.upload_test_files()

        # 等待文件上传完成
        await asyncio.sleep(1)

        # 2. 运行测试
        log.info("\n📦 步骤2: 运行导入测试")
        tests = S3ImportTests(setup)
        results = await tests.run_all_tests()

        # 3. 清理测试文件（可选，如果需要保留测试文件用于验证，可以注释掉）
        log.info("\n📦 步骤3: 清理测试环境")
        cleanup = input("\n是否清理测试文件？(y/n): ").strip().lower()
        if cleanup == 'y':
            setup.cleanup_test_files()
        else:
            log.info(f"⚠️  测试文件保留在: {setup.bucket_name}/{setup.test_prefix}")

        log.info("\n" + "🎉"*30)
        log.info("测试完成!")
        log.info("🎉"*30)

    except Exception as e:
        log.error(f"\n💥 测试过程中出现错误: {str(e)}")
        log.error("\n尝试清理测试文件...")
        try:
            setup.cleanup_test_files()
        except:
            pass
        raise


if __name__ == '__main__':
    """
    使用说明:

    1. 确保 MinIO 服务已启动
    2. 确保数据库连接正常
    3. 修改测试用户信息（test_user_id, test_username, test_dept_id）
    4. 运行测试: python import_service_s3_test.py

    配置检查:
    - MINIO_URL: {settings.MINIO_URL if hasattr(settings, 'MINIO_URL') else '未配置'}
    - ACCESS_KEY: {'已配置' if settings.ACCESS_KEY else '未配置'}
    - SECRET_KEY: {'已配置' if settings.SECRET_KEY else '未配置'}
    - BUCKET_NAME: {settings.BUCKET_NAME if hasattr(settings, 'BUCKET_NAME') else '未配置'}
    """

    # 打印配置信息
    print("\n" + "="*60)
    print("⚙️  配置信息")
    print("="*60)
    print(f"MinIO URL: {settings.MINIO_URL if hasattr(settings, 'MINIO_URL') else '未配置'}")
    print(f"Access Key: {'已配置' if settings.ACCESS_KEY else '未配置'}")
    print(f"Secret Key: {'已配置' if settings.SECRET_KEY else '未配置'}")
    print(f"Bucket Name: {settings.BUCKET_NAME if hasattr(settings, 'BUCKET_NAME') else '未配置'}")
    print("="*60 + "\n")

    # 检查必要的配置
    if not settings.ACCESS_KEY or not settings.SECRET_KEY:
        print("❌ 错误: MinIO 配置不完整，请检查 settings 配置")
        sys.exit(1)

    # 运行测试
    asyncio.run(main())
