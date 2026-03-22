-- Migrate sys_doc.type from Chinese to English
-- Run once against the database after deploying the updated code

UPDATE sys_doc SET type = 'text'        WHERE type = '文本';
UPDATE sys_doc SET type = 'spreadsheet' WHERE type = '表格';
UPDATE sys_doc SET type = 'image'       WHERE type = '图片';
UPDATE sys_doc SET type = 'media'       WHERE type = '媒体';
UPDATE sys_doc SET type = 'email'       WHERE type = '邮件';
UPDATE sys_doc SET type = 'document'    WHERE type = '文档';
UPDATE sys_doc SET type = 'archive'     WHERE type = '压缩包';
UPDATE sys_doc SET type = 'pdf'         WHERE type = 'PDF';
UPDATE sys_doc SET type = 'ppt'         WHERE type = 'PPT';
UPDATE sys_doc SET type = 'html'        WHERE type = 'HTML';
