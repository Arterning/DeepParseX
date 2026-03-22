-- 为 sys_doc 表启用行级安全策略 (RLS)
-- 执行方式：psql -U <user> -d <db> -f enable_rls_sys_doc.sql
--
-- 策略逻辑：
--   当会话变量 app.current_user_id 未设置（后台任务、定时任务场景）→ 不限制
--   当 app.is_superuser = 'true' → 不限制
--   否则只允许访问 created_by = app.current_user_id 的行
--
-- 应用层通过 user_scoped_db_session() 在每个事务开始时注入这两个变量（SET LOCAL，事务结束自动清除）

ALTER TABLE sys_doc ENABLE ROW LEVEL SECURITY;
ALTER TABLE sys_doc FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS sys_doc_owner_policy ON sys_doc;

CREATE POLICY sys_doc_owner_policy ON sys_doc
    AS PERMISSIVE
    FOR ALL
    USING (
        -- 未设置上下文（后台任务等）→ 放行
        current_setting('app.current_user_id', true) IS NULL
        OR current_setting('app.current_user_id', true) = ''
        -- 超级用户 → 放行
        OR current_setting('app.is_superuser', true) = 'true'
        -- 普通用户 → 只能访问自己创建的行
        OR created_by = current_setting('app.current_user_id', true)::integer
    )
    WITH CHECK (
        current_setting('app.current_user_id', true) IS NULL
        OR current_setting('app.current_user_id', true) = ''
        OR current_setting('app.is_superuser', true) = 'true'
        OR created_by = current_setting('app.current_user_id', true)::integer
    );
