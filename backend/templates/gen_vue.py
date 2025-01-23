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
env = Environment(loader=FileSystemLoader('templates/vue'))



ts_api_template = env.get_template('api.jinja')
ts_vue_template = env.get_template('vue.jinja')

# 定义要替换的变量
context = {
    'Entity': 'Tag',
    'path': 'tags',
    'entity': 'tag',
    'MenuName': '标签管理',
}



save_file(ts_api_template, context, f"templates/{context["entity"]}.ts")
save_file(ts_vue_template, context, "templates/index.vue")