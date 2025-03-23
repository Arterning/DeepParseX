INSERT INTO sys_dept (id, name, level, sort, leader, phone, email, status, del_flag, parent_id, created_time, updated_time)
VALUES (1, 'test', 0, 0, null, null, null, 1, false, null, '2023-06-26 17:13:45', null);


INSERT INTO sys_role (id, name, data_scope, status, remark, created_time, updated_time)
VALUES (1, 'test', 2, 1, null, '2023-06-26 17:13:45', null);

INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (3, '首页', 'Workplace', 0, 0, 'IconApps', 'workplace', 1, '/dashboard/workplace/index.vue', null, 1, 1, 1, null, null, '2023-07-27 19:17:59.000000 +00:00', '2025-02-24 06:36:27.432738 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (4, '日志', 'log', 0, 12, 'IconBug', 'log', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:19:59.000000 +00:00', '2025-02-25 06:06:02.217428 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (5, '登录日志', 'Login', 0, 0, null, 'login', 1, '/log/login/index.vue', null, 1, 1, 1, null, 4, '2023-07-27 19:20:56.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (6, '操作日志', 'Opera', 0, 0, null, 'opera', 1, '/log/opera/index.vue', null, 1, 1, 1, null, 4, '2023-07-27 19:21:28.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (7, '系统管理', 'admin', 0, 10, 'IconSettings', 'admin', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:23:00.000000 +00:00', '2025-02-25 06:05:44.744045 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (8, '部门管理', 'SysDept', 0, 0, null, 'sys-dept', 1, '/admin/dept/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:23:42.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (9, '新增', '', 0, 0, null, null, 2, null, 'sys:dept:add', 1, 1, 1, null, 8, '2024-01-07 11:37:00.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (10, '编辑', '', 0, 0, null, null, 2, null, 'sys:dept:edit', 1, 1, 1, null, 8, '2024-01-07 11:37:29.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (11, '删除', '', 0, 0, null, null, 2, null, 'sys:dept:del', 1, 1, 1, null, 8, '2024-01-07 11:37:44.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (12, 'API管理', 'SysApi', 0, 1, null, 'sys-api', 1, '/admin/api/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:24:12.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (13, '新增', '', 0, 0, null, null, 2, null, 'sys:api:add', 1, 1, 1, null, 12, '2024-01-07 11:57:09.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (14, '编辑', '', 0, 0, null, null, 2, null, 'sys:api:edit', 1, 1, 1, null, 12, '2024-01-07 11:57:44.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (15, '删除', '', 0, 0, null, null, 2, null, 'sys:api:del', 1, 1, 1, null, 12, '2024-01-07 11:57:56.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (16, '用户管理', 'SysUser', 0, 0, null, 'sys-user', 1, '/admin/user/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:25:13.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (17, '编辑用户角色', '', 0, 0, null, null, 2, null, 'sys:user:role:edit', 1, 1, 1, null, 16, '2024-01-07 12:04:20.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (18, '注销', '', 0, 0, null, null, 2, null, 'sys:user:del', 1, 1, 1, '用户注销 != 用户登出，注销之后用户将从数据库删除', 16, '2024-01-07 02:28:09.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (19, '角色管理', 'SysRole', 0, 2, null, 'sys-role', 1, '/admin/role/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:25:45.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (20, '新增', '', 0, 0, null, null, 2, null, 'sys:role:add', 1, 1, 1, null, 19, '2024-01-07 11:58:37.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (21, '编辑', '', 0, 0, null, null, 2, null, 'sys:role:edit', 1, 1, 1, null, 19, '2024-01-07 11:58:52.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (22, '删除', '', 0, 0, null, null, 2, null, 'sys:role:del', 1, 1, 1, null, 19, '2024-01-07 11:59:07.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (23, '编辑角色菜单', '', 0, 0, null, null, 2, null, 'sys:role:menu:edit', 1, 1, 1, null, 19, '2024-01-07 01:59:39.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (24, '菜单管理', 'SysMenu', 0, 2, null, 'sys-menu', 1, '/admin/menu/index.vue', null, 1, 1, 1, null, 7, '2023-07-27 19:45:29.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (25, '新增', '', 0, 0, null, null, 2, null, 'sys:menu:add', 1, 1, 1, null, 24, '2024-01-07 12:01:24.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (26, '编辑', '', 0, 0, null, null, 2, null, 'sys:menu:edit', 1, 1, 1, null, 24, '2024-01-07 12:01:34.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (27, '删除', '', 0, 0, null, null, 2, null, 'sys:menu:del', 1, 1, 1, null, 24, '2024-01-07 12:01:48.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (28, '系统监控', 'monitor', 0, 11, 'IconComputer', 'monitor', 0, null, null, 1, 1, 1, null, null, '2023-07-27 19:27:08.000000 +00:00', '2025-02-25 06:05:55.125484 +00:00');
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (29, 'Redis监控', 'Redis', 0, 0, null, 'redis', 1, '/monitor/redis/index.vue', 'sys:monitor:redis', 1, 1, 1, null, 28, '2023-07-27 19:28:03.000000 +00:00', null);
INSERT INTO sys_menu (id, title, name, level, sort, icon, path, menu_type, component, perms, status, show, cache, remark, parent_id, created_time, updated_time) VALUES (30, '服务器监控', 'Server', 0, 0, null, 'server', 1, '/monitor/server/index.vue', 'sys:monitor:server', 1, 1, 1, null, 28, '2023-07-27 19:28:29.000000 +00:00', null);

INSERT INTO sys_role_menu (id, role_id, menu_id)
VALUES (1, 1, 3);

-- 密码明文：123456
INSERT INTO sys_user (id, uuid, username, nickname, password, salt, email, is_superuser, is_staff, status, is_multi_login, avatar, phone, join_time, last_login_time, dept_id, created_time, updated_time)
VALUES (1, 'af4c804f-3966-4949-ace2-3bb7416ea926', 'admin', '用户88888', '$2b$12$RJXAtJodRw37ZQGxTPlu0OH.aN5lNXG6yvC4Tp9GIQEBmMY/YCc.m', 'bcNjV', 'admin@example.com', true, true, 1, true, null, null, '2023-06-26 17:13:45', null, 1, '2023-06-26 17:13:45', null);

INSERT INTO sys_user_role (id, user_id, role_id)
VALUES (1, 1, 1);


SELECT setval('sys_menu_id_seq', (SELECT MAX(id) FROM sys_menu));
SELECT setval('sys_dept_id_seq', (SELECT MAX(id) FROM sys_dept));
SELECT setval('sys_user_id_seq', (SELECT MAX(id) FROM sys_user));
SELECT setval('sys_user_role_id_seq', (SELECT MAX(id) FROM sys_user_role));
SELECT setval('sys_role_menu_id_seq', (SELECT MAX(id) FROM sys_role_menu));
SELECT setval('sys_role_id_seq', (SELECT MAX(id) FROM sys_role));
