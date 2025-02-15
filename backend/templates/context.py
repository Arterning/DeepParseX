
# 定义要替换的变量
tag_context = {
    'app_name': 'admin',
    'table_name_en': 'sys_tag',
    'table_name_zh': '标签',
    'table_name_class': 'Tag',
    'file_prefix': 'tag',
    'schema_name': 'Tag',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '标签名称',
        },
    ]
}


person_context = {
    'app_name': 'admin',
    'table_name_en': 'sys_person',
    'table_name_zh': '人物',
    'table_name_class': 'Person',
    'file_prefix': 'person',
    'schema_name': 'Person',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '人物名称',
        },
    ]
}