INSERT INTO sys_dept (id, name, level, sort, leader, phone, email, status, del_flag, parent_id, created_time, updated_time)
VALUES (1, 'test', 0, 0, null, null, null, 1, false, null, '2023-06-26 17:13:45', null);


INSERT INTO sys_role (id, name, data_scope, status, remark, created_time, updated_time)
VALUES (1, 'test', 2, 1, null, '2023-06-26 17:13:45', null);

-- 先插入父菜单
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (3, '首页', 'Workplace', 0, 0, 'IconApps', 'workplace', 1, '/dashboard/workplace/index.vue', null, 1, 1, 1, null, null, '2023-07-27 19:17:59.000000 +00:00', '2025-02-24 06:36:27.432738 +00:00');

INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (4, '日志', 'log', 0, 12, 'IconBug', 'log', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:19:59.000000 +00:00', '2025-02-25 06:06:02.217428 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (5, '登录日志', 'Login', 0, 0, null, 'login', 1, '/log/login/index.vue', null, 1, 1, 1, null, 4, '2023-07-27 19:20:56.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (6, '操作日志', 'Opera', 0, 0, null, 'opera', 1, '/log/opera/index.vue', null, 1, 1, 1, null, 4, '2023-07-27 19:21:28.000000 +00:00', null);

INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (7, '系统管理', 'admin', 0, 10, 'IconSettings', 'admin', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:23:00.000000 +00:00', '2025-02-25 06:05:44.744045 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (8, '部门管理', 'SysDept', 0, 0, null, 'sys-dept', 1, '/admin/dept/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:23:42.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (12, 'API管理', 'SysApi', 0, 1, null, 'sys-api', 1, '/admin/api/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:24:12.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (16, '用户管理', 'SysUser', 0, 0, null, 'sys-user', 1, '/admin/user/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:25:13.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (19, '角色管理', 'SysRole', 0, 2, null, 'sys-role', 1, '/admin/role/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:25:45.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (24, '菜单管理', 'SysMenu', 0, 2, null, 'sys-menu', 1, '/admin/menu/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:45:29.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (28, '系统监控', 'monitor', 0, 11, 'IconComputer', 'monitor', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:27:08.000000 +00:00', '2025-02-25 06:05:55.125484 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (31, '工作台', 'work', 0, 6, 'IconDesktop', null, 0, null, null, 1, 1, 1, null, null, '2025-02-25 06:02:32.001894 +00:00', '2025-04-28 06:44:08.951600 +00:00');

-- 再插入子菜单
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (9, '新增', '', 0, 0, null, null, 2, null, 'sys:dept:add', 1, 1, 1, null, 8, '2024-01-07 11:37:00.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (10, '编辑', '', 0, 0, null, null, 2, null, 'sys:dept:edit', 1, 1, 1, null, 8, '2024-01-07 11:37:29.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (11, '删除', '', 0, 0, null, null, 2, null, 'sys:dept:del', 1, 1, 1, null, 8, '2024-01-07 11:37:44.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (13, '新增', '', 0, 0, null, null, 2, null, 'sys:api:add', 1, 1, 1, null, 12, '2024-01-07 11:57:09.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (14, '编辑', '', 0, 0, null, null, 2, null, 'sys:api:edit', 1, 1, 1, null, 12, '2024-01-07 11:57:44.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (15, '删除', '', 0, 0, null, null, 2, null, 'sys:api:del', 1, 1, 1, null, 12, '2024-01-07 11:57:56.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (17, '编辑用户角色', '', 0, 0, null, null, 2, null, 'sys:user:role:edit', 1, 1, 1, null, 16, '2024-01-07 12:04:20.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (18, '注销', '', 0, 0, null, null, 2, null, 'sys:user:del', 1, 1, 1, '用户注销 != 用户登出，注销之后用户将从数据库删除', 16, '2024-01-07 02:28:09.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (20, '新增', '', 0, 0, null, null, 2, null, 'sys:role:add', 1, 1, 1, null, 19, '2024-01-07 11:58:37.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (21, '编辑', '', 0, 0, null, null, 2, null, 'sys:role:edit', 1, 1, 1, null, 19, '2024-01-07 11:58:52.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (22, '删除', '', 0, 0, null, null, 2, null, 'sys:role:del', 1, 1, 1, null, 19, '2024-01-07 11:59:07.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (23, '编辑角色菜单', '', 0, 0, null, null, 2, null, 'sys:role:menu:edit', 1, 1, 1, null, 19, '2024-01-07 01:59:39.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (25, '新增', '', 0, 0, null, null, 2, null, 'sys:menu:add', 1, 1, 1, null, 24, '2024-01-07 12:01:24.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (26, '编辑', '', 0, 0, null, null, 2, null, 'sys:menu:edit', 1, 1, 1, null, 24, '2024-01-07 12:01:34.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (27, '删除', '', 0, 0, null, null, 2, null, 'sys:menu:del', 1, 1, 1, null, 24, '2024-01-07 12:01:48.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (29, 'Redis监控', 'Redis', 0, 0, null, 'redis', 1, '/monitor/redis/index.vue', 'sys:monitor:redis', 1, 1, 1, null, 28, '2023-07-27 19:28:03.000000 +00:00', null);
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (30, '服务器监控', 'Server', 0, 0, null, 'server', 1, '/monitor/server/index.vue', 'sys:monitor:server', 1, 1, 1, null, 28, '2023-07-27 19:28:29.000000 +00:00', null);


INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (45, '文件上传', 'Upload', 0, 1, 'IconUpload', 'upload', 1, '/data/upload/index.vue', 'sys:task:run', 1, 1, 1, null, null, '2024-10-05 11:41:57.239227 +00:00', '2025-04-17 08:01:03.509093 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (64, '数据搜索', 'search', 0, 2, 'IconSearch', 'search', 1, '/data/search/index.vue', null, 1, 1, 1, null, null, '2025-02-24 06:37:54.959044 +00:00', '2025-02-24 06:38:20.821445 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (59, '智能助手', 'aiAssistant', 0, 3, 'IconRobot', 'assistant', 1, '/data/aiAssistant/index.vue', null, 1, 1, 1, null, null, '2025-02-25 09:24:14.229989 +00:00', '2025-02-28 07:51:41.153866 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (43, '数据治理', 'data', 0, 4, 'IconApps', 'data', 1, '', null, 1, 1, 1, null, null, '2024-10-05 08:20:22.158815 +00:00', '2025-05-26 06:17:34.711261 +00:00');

INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (46, '文件详情', 'DocDetail', 0, 999, null, 'doc-detail', 1, '/data/doc-detail/index.vue', null, 1, 0, 1, null, 43, '2024-10-23 14:02:28.496258 +00:00', '2025-03-07 06:32:22.535773 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (44, '文件管理', 'Doc', 0, 1, 'IconFile', 'doc', 1, '/data/doc/index.vue', null, 1, 1, 1, null, 43, '2024-10-05 08:22:03.277761 +00:00', '2025-04-16 08:09:34.952849 +00:00');

INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (52, '标签管理', 'Tag', 0, 0, 'IconTag', 'tag', 1, '/data/tag/index.vue', null, 1, 1, 1, null, 31, '2025-01-23 09:11:18.733064 +00:00', '2025-02-25 06:04:14.394907 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (70, '我的收藏', 'Collection', 0, 2, 'IconStarFill', 'collection', 1, '/data/star/index.vue', null, 1, 1, 1, null, 31, '2025-06-04 09:06:36.642210 +00:00', null);

INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (60, '要素提取', 'Entity', 0, 2, 'IconCommon', 'entity', 1, '/data/entity/index.vue', null, 1, 1, 1, null, 43, '2025-02-24 02:17:56.565979 +00:00', '2025-08-20 07:17:19.009186 +00:00');

INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (66, '邮件详情', 'MailMsgDetail', 0, 7, null, 'mailmsg-detail', 1, '/data/mailmsg-detail/index.vue', null, 1, 0, 1, null, 43, '2025-04-16 08:03:59.294626 +00:00', '2025-09-20 06:59:40.661819 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (75, '邮件处理', 'Mail', 0, 3, 'IconEmail', 'mail', 1, '/data/mail/index.vue', null, 1, 1, 1, null, 43, '2025-09-25 01:21:09.669394 +00:00', '2025-09-25 01:21:42.216650 +00:00');
INSERT INTO public.sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (74, '邮箱详情', 'MailBoxDetail', 0, 6, null, 'mailbox-detail', 1, '/data/mailbox-detail/index.vue', null, 1, 0, 1, null, 43, '2025-09-20 06:58:26.089310 +00:00', '2025-09-20 06:59:15.946532 +00:00');

INSERT INTO sys_role_menu (id, role_id, menu_id)
VALUES (1, 1, 7);

-- 密码明文：123456
INSERT INTO sys_user (id, uuid, username, nickname, password, salt, email, is_superuser, is_staff, status, is_multi_login, avatar, phone, join_time, last_login_time, dept_id, created_time, updated_time)
VALUES (1, 'af4c804f-3966-4949-ace2-3bb7416ea926', 'admin', '用户88888', '$2b$12$RJXAtJodRw37ZQGxTPlu0OH.aN5lNXG6yvC4Tp9GIQEBmMY/YCc.m', 'bcNjV', 'admin@example.com', true, true, 1, true, null, null, '2023-06-26 17:13:45', null, 1, '2023-06-26 17:13:45', null);

INSERT INTO sys_user_role (id, user_id, role_id)
VALUES (1, 1, 1);

CREATE INDEX idx_sys_doc_fulltext ON sys_doc USING gin (to_tsvector('simple', doc_tokens::text));


SELECT setval('sys_menu_id_seq', (SELECT MAX(id) FROM sys_menu));
SELECT setval('sys_dept_id_seq', (SELECT MAX(id) FROM sys_dept));
SELECT setval('sys_user_id_seq', (SELECT MAX(id) FROM sys_user));
SELECT setval('sys_user_role_id_seq', (SELECT MAX(id) FROM sys_user_role));
SELECT setval('sys_role_menu_id_seq', (SELECT MAX(id) FROM sys_role_menu));
SELECT setval('sys_role_id_seq', (SELECT MAX(id) FROM sys_role));
