#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: I001
import logging
import sys
import re

from anyio import run
from pathlib import Path

sys.path.append('../')


from jinja2 import Environment, FileSystemLoader
from sqlalchemy import String, Integer, Boolean, Text, DateTime, Date, Float, JSON
from sqlalchemy.dialects.mysql import LONGTEXT, MEDIUMTEXT, TINYTEXT
from sqlalchemy.orm import DeclarativeBase


def camel_to_snake(name):
    """将 CamelCase 转换为 snake_case"""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def get_python_type(column):
    """从 SQLAlchemy 列类型获取 Python 类型字符串"""
    col_type = column.type

    # 处理常见的 SQLAlchemy 类型
    if isinstance(col_type, (String, Text, LONGTEXT, MEDIUMTEXT, TINYTEXT)):
        return 'str'
    elif isinstance(col_type, Integer):
        return 'int'
    elif isinstance(col_type, Boolean):
        return 'bool'
    elif isinstance(col_type, Float):
        return 'float'
    elif isinstance(col_type, (DateTime, Date)):
        return 'datetime'
    elif isinstance(col_type, JSON):
        return 'dict'
    else:
        # 默认返回 str
        return 'str'


def get_sqlalchemy_type(column):
    """从 SQLAlchemy 列类型获取类型字符串"""
    col_type = column.type

    if isinstance(col_type, LONGTEXT):
        return 'LONGTEXT'
    elif isinstance(col_type, MEDIUMTEXT):
        return 'MEDIUMTEXT'
    elif isinstance(col_type, TINYTEXT):
        return 'TINYTEXT'
    elif isinstance(col_type, String):
        return 'String'
    elif isinstance(col_type, Text):
        return 'Text'
    elif isinstance(col_type, Integer):
        return 'Integer'
    elif isinstance(col_type, Boolean):
        return 'Boolean'
    elif isinstance(col_type, Float):
        return 'Float'
    elif isinstance(col_type, DateTime):
        return 'DateTime'
    elif isinstance(col_type, Date):
        return 'Date'
    elif isinstance(col_type, JSON):
        return 'JSON'
    else:
        return 'String'


def extract_chinese_name(docstring):
    """从 docstring 中提取中文名称（去掉"表"字）"""
    if not docstring:
        return ''

    # 提取第一行
    first_line = docstring.strip().split('\n')[0].strip()

    # 去掉末尾的"表"字
    if first_line.endswith('表'):
        return first_line[:-1]

    return first_line


def generate_context_from_model(model_class, app_name='admin'):
    """
    从 SQLAlchemy 模型类自动生成 context

    Args:
        model_class: SQLAlchemy 模型类
        app_name: 应用名称，默认为 'admin'

    Returns:
        dict: 生成的 context 字典
    """
    # 获取表名
    table_name_en = model_class.__tablename__

    # 获取类名
    table_name_class = model_class.__name__

    # 从 docstring 提取中文名称
    table_name_zh = extract_chinese_name(model_class.__doc__)

    # 生成 file_prefix 和 schema_name
    file_prefix = camel_to_snake(table_name_class)
    schema_name = table_name_class

    # 提取字段信息
    models = []
    have_datetime_column = False

    # 遍历所有列
    for column in model_class.__table__.columns:
        # 跳过 relationship 字段（它们不在 __table__.columns 中）

        column_info = {
            'name': column.name,
            'is_nullable': column.nullable,
            'pd_type': get_python_type(column),
            'type': get_sqlalchemy_type(column),
            'comment': column.comment or ''
        }

        # 检查是否有日期时间列
        if column_info['type'] in ['DateTime', 'Date']:
            have_datetime_column = True

        models.append(column_info)

    # 生成 context
    context = {
        'app_name': app_name,
        'table_name_en': table_name_en,
        'table_name_zh': table_name_zh,
        'table_name_class': table_name_class,
        'file_prefix': file_prefix,
        'schema_name': schema_name,
        'have_datetime_column': have_datetime_column,
        'models': models
    }

    return context


def save_file(template, context, path):
    # 渲染模板
    output = template.render(context)

    # 输出文件路径
    output_file = Path(path)

    # 将渲染后的内容写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(output)

    print(f"文件已保存到: {output_file.resolve()}")


# 创建模板环境，指定模板文件所在的目录
env = Environment(loader=FileSystemLoader('templates/py'))

# 加载模板
model_template = env.get_template('model.jinja')
service_template = env.get_template('service.jinja')
crud_template = env.get_template('crud.jinja')
api_template = env.get_template('api.jinja')
schema_template = env.get_template('schema.jinja')


if __name__ == '__main__':
    # ============================================================
    # 方式一：从已存在的模型类自动生成（推荐）
    # ============================================================
    # 导入你要生成代码的模型类
    from backend.app.admin.model.sys_chat_session import ChatSession

    # 自动生成 context
    context = generate_context_from_model(ChatSession, app_name='admin')

    # 打印生成的 context，方便查看
    print("Generated context:")
    print(f"  table_name_en: {context['table_name_en']}")
    print(f"  table_name_zh: {context['table_name_zh']}")
    print(f"  table_name_class: {context['table_name_class']}")
    print(f"  file_prefix: {context['file_prefix']}")
    print(f"  schema_name: {context['schema_name']}")
    print(f"  have_datetime_column: {context['have_datetime_column']}")
    print(f"  models: {len(context['models'])} fields")
    for model in context['models']:
        print(f"    - {model['name']}: {model['type']} ({'nullable' if model['is_nullable'] else 'not null'}) - {model['comment']}")
    print()

    # ============================================================
    # 方式二：手动定义 context（原有方式，仍然保留）
    # ============================================================
    # context = {
    #     'app_name': 'admin',
    #     'table_name_en': 'sys_note',
    #     'table_name_zh': '笔记',
    #     'table_name_class': 'Note',
    #     'file_prefix': 'note',
    #     'schema_name': 'Note',
    #     'have_datetime_column': True,
    #     'models': [
    #         {
    #             'name': 'name',
    #             'is_nullable': False,
    #             'pd_type': 'str',
    #             'type': 'String',
    #             'comment': '笔记名称',
    #         },
    #         {
    #             'name': 'content',
    #             'is_nullable': False,
    #             'pd_type': 'str',
    #             'type': 'String',
    #             'comment': '笔记内容',
    #         },
    #     ]
    # }

    # 生成文件路径
    base = "app/admin/"
    table_name_en = context["table_name_en"]
    file_prefix = context["file_prefix"]
    # model_file = base + f"model/{table_name_en}.py"  # 通常不需要重新生成 model 文件
    schema_file = base + f"schema/{file_prefix}.py"
    crud_file = base + f"crud/crud_{file_prefix}.py"
    service_file = base + f"service/{file_prefix}_service.py"
    api_file = base + f"api/v1/sys/{file_prefix}.py"

    # 生成文件
    # save_file(model_template, context, model_file)  # 通常不需要重新生成 model 文件
    save_file(schema_template, context, schema_file)
    save_file(crud_template, context, crud_file)
    save_file(service_template, context, service_file)
    save_file(api_template, context, api_file)

    print("""
next you may want to execute :

alembic revision --autogenerate

alembic upgrade head
      """)