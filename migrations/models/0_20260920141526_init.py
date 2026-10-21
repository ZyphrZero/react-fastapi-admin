from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "sys_api" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "path" VARCHAR(100) NOT NULL /* API路径 */,
    "method" VARCHAR(6) NOT NULL /* 请求方法 */,
    "summary" VARCHAR(500) NOT NULL /* 请求简介 */,
    "tags" VARCHAR(100) NOT NULL /* API标签 */
);
CREATE INDEX IF NOT EXISTS "idx_sys_api_path_995e70" ON "sys_api" ("path");
CREATE INDEX IF NOT EXISTS "idx_sys_api_method_4e2013" ON "sys_api" ("method");
CREATE INDEX IF NOT EXISTS "idx_sys_api_summary_300306" ON "sys_api" ("summary");
CREATE INDEX IF NOT EXISTS "idx_sys_api_tags_d39762" ON "sys_api" ("tags");
CREATE TABLE IF NOT EXISTS "sys_audit_log" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "user_id" INT NOT NULL /* 用户ID */,
    "username" VARCHAR(64) NOT NULL DEFAULT '' /* 用户名称 */,
    "module" VARCHAR(64) NOT NULL DEFAULT '' /* 功能模块 */,
    "summary" VARCHAR(128) NOT NULL DEFAULT '' /* 请求描述 */,
    "method" VARCHAR(10) NOT NULL DEFAULT '' /* 请求方法 */,
    "path" VARCHAR(255) NOT NULL DEFAULT '' /* 请求路径 */,
    "status" INT NOT NULL DEFAULT -1 /* 状态码 */,
    "response_time" INT NOT NULL DEFAULT 0 /* 响应时间(单位ms) */,
    "request_args" JSON /* 请求参数 */,
    "response_body" JSON /* 返回数据 */,
    "ip_address" VARCHAR(64) NOT NULL DEFAULT '' /* IP地址 */,
    "user_agent" VARCHAR(512) NOT NULL DEFAULT '' /* 用户代理 */,
    "operation_type" VARCHAR(32) NOT NULL DEFAULT '' /* 操作类型 */,
    "log_level" VARCHAR(16) NOT NULL DEFAULT 'info' /* 日志级别 */,
    "is_deleted" INT NOT NULL DEFAULT 0 /* 是否已删除 */
);
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_user_id_3961c9" ON "sys_audit_log" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_usernam_a75af4" ON "sys_audit_log" ("username");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_module_d1630c" ON "sys_audit_log" ("module");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_summary_9dc70b" ON "sys_audit_log" ("summary");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_method_f1d610" ON "sys_audit_log" ("method");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_path_19963a" ON "sys_audit_log" ("path");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_status_eaf40d" ON "sys_audit_log" ("status");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_respons_3cc155" ON "sys_audit_log" ("response_time");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_ip_addr_250f7b" ON "sys_audit_log" ("ip_address");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_user_ag_3f9f35" ON "sys_audit_log" ("user_agent");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_operati_5028be" ON "sys_audit_log" ("operation_type");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_log_lev_60dc5a" ON "sys_audit_log" ("log_level");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_is_dele_bd4e9a" ON "sys_audit_log" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_created_60ca44" ON "sys_audit_log" ("created_at", "username");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_created_efca1c" ON "sys_audit_log" ("created_at", "module");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_created_c6f2ff" ON "sys_audit_log" ("created_at", "status");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_created_ca929f" ON "sys_audit_log" ("created_at", "operation_type");
CREATE INDEX IF NOT EXISTS "idx_sys_audit_l_created_120b5b" ON "sys_audit_log" ("created_at", "log_level");
CREATE TABLE IF NOT EXISTS "sys_rate_limit_bucket" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "bucket_key" VARCHAR(255) NOT NULL UNIQUE /* 限流桶键 */,
    "count" INT NOT NULL DEFAULT 0 /* 窗口内请求次数 */,
    "expires_at" BIGINT NOT NULL /* 过期时间戳 */
);
CREATE INDEX IF NOT EXISTS "idx_sys_rate_li_bucket__2cc579" ON "sys_rate_limit_bucket" ("bucket_key");
CREATE INDEX IF NOT EXISTS "idx_sys_rate_li_expires_65de95" ON "sys_rate_limit_bucket" ("expires_at");
CREATE TABLE IF NOT EXISTS "sys_role" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "name" VARCHAR(20) NOT NULL UNIQUE /* 角色名称 */,
    "desc" VARCHAR(500) /* 角色描述 */,
    "menu_paths" JSON NOT NULL /* 菜单权限路径 */,
    "api_ids" JSON NOT NULL /* API权限ID列表 */
);
CREATE INDEX IF NOT EXISTS "idx_sys_role_name_616e55" ON "sys_role" ("name");
CREATE TABLE IF NOT EXISTS "sys_system_setting" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "key" VARCHAR(100) NOT NULL UNIQUE /* 配置键 */,
    "value" JSON NOT NULL /* 配置值 */,
    "description" VARCHAR(255) /* 配置说明 */
);
CREATE INDEX IF NOT EXISTS "idx_sys_system__key_020268" ON "sys_system_setting" ("key");
CREATE TABLE IF NOT EXISTS "sys_user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 创建时间 */,
    "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP /* 更新时间 */,
    "username" VARCHAR(20) NOT NULL UNIQUE /* 用户名称 */,
    "nickname" VARCHAR(30) /* 昵称 */,
    "avatar" VARCHAR(500) /* 头像地址 */,
    "email" VARCHAR(255) UNIQUE /* 邮箱 */,
    "phone" VARCHAR(20) /* 电话 */,
    "password" VARCHAR(128) /* 密码 */,
    "is_active" INT NOT NULL DEFAULT 1 /* 是否激活 */,
    "is_superuser" INT NOT NULL DEFAULT 0 /* 是否为超级管理员 */,
    "last_login" TIMESTAMP /* 最后登录时间 */,
    "session_version" INT NOT NULL DEFAULT 0 /* 会话版本 */,
    "refresh_token_jti" VARCHAR(32) /* 当前刷新令牌标识 */
);
CREATE INDEX IF NOT EXISTS "idx_sys_user_usernam_29caba" ON "sys_user" ("username");
CREATE INDEX IF NOT EXISTS "idx_sys_user_nicknam_f5cda9" ON "sys_user" ("nickname");
CREATE INDEX IF NOT EXISTS "idx_sys_user_email_451315" ON "sys_user" ("email");
CREATE INDEX IF NOT EXISTS "idx_sys_user_phone_7ed3ec" ON "sys_user" ("phone");
CREATE INDEX IF NOT EXISTS "idx_sys_user_is_acti_1ce30a" ON "sys_user" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_sys_user_is_supe_05cdbf" ON "sys_user" ("is_superuser");
CREATE INDEX IF NOT EXISTS "idx_sys_user_last_lo_8b355d" ON "sys_user" ("last_login");
CREATE INDEX IF NOT EXISTS "idx_sys_user_session_06d54b" ON "sys_user" ("session_version");
CREATE INDEX IF NOT EXISTS "idx_sys_user_refresh_c89662" ON "sys_user" ("refresh_token_jti");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "sys_user_role" (
    "sys_user_id" INT NOT NULL REFERENCES "sys_user" ("id") ON DELETE CASCADE,
    "role_id" INT NOT NULL REFERENCES "sys_role" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_sys_user_ro_sys_use_ed7daf" ON "sys_user_role" ("sys_user_id", "role_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
    "/AeyQSG5"
)
