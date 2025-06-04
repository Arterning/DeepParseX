
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

star_collect_context = {
    'app_name': 'admin',
    'table_name_en': 'sys_star_collect',
    'table_name_zh': '收藏',
    'table_name_class': 'StarCollect',
    'file_prefix': 'star_collect',
    'schema_name': 'StarCollect',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name', 
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '收藏名称',
        },
        {
            'name': 'description',
            'is_nullable': True,
            'pd_type': 'str',            
            'type': 'String',
            'comment': '收藏描述',
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



org_context = {
    'app_name': 'admin',
    'table_name_en': 'sys_org',
    'table_name_zh': '组织',
    'table_name_class': 'Org',
    'file_prefix': 'org',
    'schema_name': 'Org',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '组织名称',
        },
    ]
}



news_context = {
    'app_name': 'admin',
    'table_name_en': 'sys_news',
    'table_name_zh': '新闻',
    'table_name_class': 'News',
    'file_prefix': 'news',
    'schema_name': 'News',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '新闻标题',
        },
    ]
}



subject_context = {
    'app_name': 'admin',
    'table_name_en': 'sys_subject',
    'table_name_zh': '议题',
    'table_name_class': 'Subject',
    'file_prefix': 'subject',
    'schema_name': 'Subject',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '议题名称',
        },
    ]
}




mail_box_context = {
    'app_name': 'admin',
    'table_name_en': 'mail_box',
    'table_name_zh': '邮箱',
    'table_name_class': 'MailBox',
    'file_prefix': 'mail_box',
    'schema_name': 'MailBox',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '邮箱地址',
        },
    ]
}



mail_msg_context = {
    'app_name': 'admin',
    'table_name_en': 'mail_msg',
    'table_name_zh': '邮件',
    'table_name_class': 'MailMsg',
    'file_prefix': 'mail_msg',
    'schema_name': 'MailMsg',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '邮件标题',
        },
    ]
}



social_account_context = {
    'app_name': 'admin',
    'table_name_en': 'social_account',
    'table_name_zh': '社交账户',
    'table_name_class': 'SocialAccount',
    'file_prefix': 'social_account',
    'schema_name': 'SocialAccount',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '社交账户名称',
        },
    ]
}


social_account_post_context = {
    'app_name': 'admin',
    'table_name_en': 'social_account_post',
    'table_name_zh': '社交帖子',
    'table_name_class': 'SocialAccountPost',
    'file_prefix': 'social_account_post',
    'schema_name': 'SocialAccountPost',
    'have_datetime_column': True,
    'models': [
        {
            'name': 'name',
            'is_nullable': False,
            'pd_type': 'str',
            'type': 'String',
            'comment': '名称',
        },
    ]
}