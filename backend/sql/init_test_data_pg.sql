INSERT INTO sys_dept (id, name, level, sort, leader, phone, email, status, del_flag, parent_id, created_time, updated_time)
VALUES (1, 'test', 0, 0, null, null, null, 1, false, null, '2023-06-26 17:13:45', null);


INSERT INTO sys_role (id, name, data_scope, status, remark, created_time, updated_time)
VALUES (1, 'test', 2, 1, null, '2023-06-26 17:13:45', null);

INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, "show", cache, remark, parent_id, created_time, updated_time)
VALUES  (1, '测试', 'test', 0, 0, '', null, 0, null, null, 0, 0, 1, null, null, '2023-07-27 19:14:10', null),
        (2, '仪表盘', 'dashboard', 0, 0, 'IconDashboard', 'dashboard', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:15:45', null),
        (3, '工作台', 'Workplace', 0, 0, null, 'workplace', 1, '/dashboard/workplace/index.vue', null, 1, 1, 1, null, 2, '2023-07-27 19:17:59', null),
        (4, '日志', 'log', 0, 66, 'IconBug', 'log', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:19:59', null),
        (5, '登录日志', 'Login', 0, 0, null, 'login', 1, '/log/login/index.vue', null, 1, 1, 1, null, 4, '2023-07-27 19:20:56', null),
        (6, '操作日志', 'Opera', 0, 0, null, 'opera', 1, '/log/opera/index.vue', null, 1, 1, 1, null, 4, '2023-07-27 19:21:28', null),
        (7, '系统管理', 'admin', 0, 6, 'IconSettings', 'admin', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:23:00', null),
        (8, '部门管理', 'SysDept', 0, 0, null, 'sys-dept', 1, '/admin/dept/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:23:42', null),
        (9, '新增', '', 0, 0, null, null, 2, null, 'sys:dept:add', 1, 1, 1, null, 8, '2024-01-07 11:37:00', null),
        (10, '编辑', '', 0, 0, null, null, 2, null, 'sys:dept:edit', 1, 1, 1, null, 8, '2024-01-07 11:37:29', null),
        (11, '删除', '', 0, 0, null, null, 2, null, 'sys:dept:del', 1, 1, 1, null, 8, '2024-01-07 11:37:44', null),
        (12, 'API管理', 'SysApi', 0, 1, null, 'sys-api', 1, '/admin/api/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:24:12', null),
        (13, '新增', '', 0, 0, null, null, 2, null, 'sys:api:add', 1, 1, 1, null, 12, '2024-01-07 11:57:09', null),
        (14, '编辑', '', 0, 0, null, null, 2, null, 'sys:api:edit', 1, 1, 1, null, 12, '2024-01-07 11:57:44', null),
        (15, '删除', '', 0, 0, null, null, 2, null, 'sys:api:del', 1, 1, 1, null, 12, '2024-01-07 11:57:56', null),
        (16, '用户管理', 'SysUser', 0, 0, null, 'sys-user', 1, '/admin/user/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:25:13', null),
        (17, '编辑用户角色', '', 0, 0, null, null, 2, null, 'sys:user:role:edit', 1, 1, 1, null, 16, '2024-01-07 12:04:20', null),
        (18, '注销', '', 0, 0, null, null, 2, null, 'sys:user:del', 1, 1, 1, '用户注销 != 用户登出，注销之后用户将从数据库删除', 16, '2024-01-07 02:28:09', null),
        (19, '角色管理', 'SysRole', 0, 2, null, 'sys-role', 1, '/admin/role/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:25:45', null),
        (20, '新增', '', 0, 0, null, null, 2, null, 'sys:role:add', 1, 1, 1, null, 19, '2024-01-07 11:58:37', null),
        (21, '编辑', '', 0, 0, null, null, 2, null, 'sys:role:edit', 1, 1, 1, null, 19, '2024-01-07 11:58:52', null),
        (22, '删除', '', 0, 0, null, null, 2, null, 'sys:role:del', 1, 1, 1, null, 19, '2024-01-07 11:59:07', null),
        (23, '编辑角色菜单', '', 0, 0, null, null, 2, null, 'sys:role:menu:edit', 1, 1, 1, null, 19, '2024-01-07 01:59:39', null),
        (24, '菜单管理', 'SysMenu', 0, 2, null, 'sys-menu', 1, '/admin/menu/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:45:29', null),
        (25, '新增', '', 0, 0, null, null, 2, null, 'sys:menu:add', 1, 1, 1, null, 24, '2024-01-07 12:01:24', null),
        (26, '编辑', '', 0, 0, null, null, 2, null, 'sys:menu:edit', 1, 1, 1, null, 24, '2024-01-07 12:01:34', null),
        (27, '删除', '', 0, 0, null, null, 2, null, 'sys:menu:del', 1, 1, 1, null, 24, '2024-01-07 12:01:48', null),
        (28, '系统监控', 'monitor', 0, 88, 'IconComputer', 'monitor', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:27:08', null),
        (29, 'Redis监控', 'Redis', 0, 0, null, 'redis', 1, '/monitor/redis/index.vue', 'sys:monitor:redis', 1, 1, 1, null, 28, '2023-07-27 19:28:03', null),
        (30, '服务器监控', 'Server', 0, 0, null, 'server', 1, '/monitor/server/index.vue', 'sys:monitor:server', 1, 1, 1, null, 28, '2023-07-27 19:28:29', null);


INSERT INTO sys_role_menu (id, role_id, menu_id)
VALUES (1, 1, 1);

-- 密码明文：123456
INSERT INTO sys_user (id, uuid, username, nickname, password, salt, email, is_superuser, is_staff, status, is_multi_login, avatar, phone, join_time, last_login_time, dept_id, created_time, updated_time)
VALUES (1, 'af4c804f-3966-4949-ace2-3bb7416ea926', 'admin', '用户88888', '$2b$12$RJXAtJodRw37ZQGxTPlu0OH.aN5lNXG6yvC4Tp9GIQEBmMY/YCc.m', 'bcNjV', 'admin@example.com', true, true, 1, true, null, null, '2023-06-26 17:13:45', null, 1, '2023-06-26 17:13:45', null);

INSERT INTO sys_user_role (id, user_id, role_id)
VALUES (1, 1, 1);


-- 文档管理
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) values (43, '数据', 'data', 0, 1, 'IconApps', 'data', 0, null, null, 1, 1, 1, null, null, '2024-10-05 08:20:22.158815 +00:00', '2024-10-05 08:23:38.257065 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) values (44, '文件管理', 'Doc', 0, 0, 'IconFile', 'doc', 1, '/data/doc/index.vue', null, 1, 1, 1, null, 43, '2024-10-05 08:22:03.277761 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) values (45, '文件上传', 'Upload', 0, 2, 'IconUpload', 'upload', 1, '/data/upload/index.vue', null, 1, 1, 1, null, 43, '2024-10-05 11:41:57.239227 +00:00', '2024-10-05 11:45:09.031372 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (46, '文件内容', 'DocDetail', 0, 0, null, 'doc-detail', 1, '/data/doc-detail/index.vue', null, 1, 0, 1, null, 43, '2024-10-23 14:02:28.496258 +00:00', '2024-10-23 14:04:54.336278 +00:00');

-- 资产和组织
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (47, '资产管理', 'Assets', 0, 1, 'IconArchive', 'assets', 1, '/data/assets/index.vue', null, 1, 1, 1, null, 43, '2024-12-12 02:56:02.698057 +00:00', '2024-12-12 09:41:34.193662 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (48, '组织管理', 'Org', 0, 2, 'IconUserGroup', 'org', 1, '/data/org/index.vue', null, 1, 1, 1, null, 43, '2024-12-12 09:42:13.817441 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (49, '组织详情', 'OrgDetail', 0, 0, null, 'org-detail', 1, '/data/org-detail/index.vue', null, 1, 0, 1, null, 43, '2024-12-13 02:45:59.328497 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (50, '资产详情', 'AssetsDetail', 0, 0, null, 'assets-detail', 1, '/data/assets-detail/index.vue', null, 1, 0, 1, null, 43, '2024-12-13 02:46:50.698312 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (52, '标签管理', 'Tag', 0, 0, 'IconTag', 'tag', 1, '/data/tag/index.vue', null, 1, 1, 1, null, 43, '2025-01-23 09:11:18.733064 +00:00', '2025-01-23 09:11:30.065039 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (51, '热点事件', 'Event', 0, 0, 'IconAlignRight', 'event', 1, '/data/event/index.vue', null, 1, 1, 1, null, 43, '2025-01-23 07:12:16.088150 +00:00', '2025-01-23 08:25:24.775709 +00:00');


CREATE INDEX idx_sys_doc_fulltext ON sys_doc USING gin (to_tsvector('simple', tokens::text));


SELECT setval('sys_menu_id_seq', (SELECT MAX(id) FROM sys_menu));
SELECT setval('sys_dept_id_seq', (SELECT MAX(id) FROM sys_dept));
SELECT setval('sys_user_id_seq', (SELECT MAX(id) FROM sys_user));
SELECT setval('sys_user_role_id_seq', (SELECT MAX(id) FROM sys_user_role));
SELECT setval('sys_role_menu_id_seq', (SELECT MAX(id) FROM sys_role_menu));
SELECT setval('sys_role_id_seq', (SELECT MAX(id) FROM sys_role));
