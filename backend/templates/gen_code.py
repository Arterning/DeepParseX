#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ruff: noqa: I001
import logging
import sys

from anyio import run
from pathlib import Path

sys.path.append('../')


from jinja2 import Environment, FileSystemLoader


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


# 定义要替换的变量
context = {
    'app_name': 'admin',
    'table_name_en': 'sys_event',
    'table_name_zh': '事件',
    'table_name_class': 'Event',
    'schema_name': 'Event',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '事件标题',
        },
        {
            'name': 'event_time',
            'is_nullable': True,
            'pd_type': 'datetime',
            'type': 'datetime',
            'comment': '事件发生时间',
        },
    ]
}

base = "app/admin/"
table_name_en = context["table_name_en"]
model_file = base + f"model/{table_name_en}.py"
schema_file = base + f"schema/{table_name_en}.py"
crud_file = base + f"crud/crud_{table_name_en}.py"
service_file = base + f"service/{table_name_en}_service.py"
api_file = base + f"api/v1/sys/{table_name_en}.py"


save_file(model_template, context, model_file)
save_file(schema_template, context, schema_file)
save_file(crud_template, context, crud_file)
save_file(service_template, context, service_file)
save_file(api_template, context, api_file)


print("""
next you may want to execute : 

alembic revision --autogenerate

alembic upgrade head
      """)