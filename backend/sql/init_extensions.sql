-- 扩展初始化：必须在建表之前执行，因为部分表（如 mail_box）的索引依赖这些扩展
CREATE EXTENSION IF NOT EXISTS pg_trgm;
