from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "api" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL /* Created at */,
    "updated_at" TIMESTAMP NOT NULL /* Updated at */,
    "path" VARCHAR(100) NOT NULL /* API path */,
    "method" VARCHAR(6) NOT NULL /* Request method */,
    "summary" VARCHAR(500) NOT NULL /* Request summary */,
    "tags" VARCHAR(100) NOT NULL /* API tag */
);
CREATE INDEX IF NOT EXISTS "idx_api_path_9ed611" ON "api" ("path");
CREATE INDEX IF NOT EXISTS "idx_api_method_a46dfb" ON "api" ("method");
CREATE INDEX IF NOT EXISTS "idx_api_summary_400f73" ON "api" ("summary");
CREATE INDEX IF NOT EXISTS "idx_api_tags_04ae27" ON "api" ("tags");
CREATE TABLE IF NOT EXISTS "audit_log" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL /* Created at */,
    "updated_at" TIMESTAMP NOT NULL /* Updated at */,
    "user_id" INT NOT NULL /* User ID */,
    "username" VARCHAR(64) NOT NULL /* Username */,
    "module" VARCHAR(64) NOT NULL /* Module */,
    "summary" VARCHAR(128) NOT NULL /* Request summary */,
    "method" VARCHAR(10) NOT NULL /* Request method */,
    "path" VARCHAR(255) NOT NULL /* Request path */,
    "status" INT NOT NULL /* Status code */,
    "response_time" INT NOT NULL /* Response time (ms) */,
    "request_args" JSON /* Request arguments */,
    "response_body" JSON /* Response body */,
    "ip_address" VARCHAR(64) NOT NULL /* IP address */,
    "user_agent" VARCHAR(512) NOT NULL /* User agent */,
    "operation_type" VARCHAR(32) NOT NULL /* Operation type */,
    "log_level" VARCHAR(16) NOT NULL /* Log level */,
    "is_deleted" INT NOT NULL /* Deleted flag */
);
CREATE INDEX IF NOT EXISTS "idx_audit_log_user_id_d5b3c4" ON "audit_log" ("user_id");
CREATE INDEX IF NOT EXISTS "idx_audit_log_usernam_b6341e" ON "audit_log" ("username");
CREATE INDEX IF NOT EXISTS "idx_audit_log_module_a9ee07" ON "audit_log" ("module");
CREATE INDEX IF NOT EXISTS "idx_audit_log_summary_88bf13" ON "audit_log" ("summary");
CREATE INDEX IF NOT EXISTS "idx_audit_log_method_2525a0" ON "audit_log" ("method");
CREATE INDEX IF NOT EXISTS "idx_audit_log_path_39c3ce" ON "audit_log" ("path");
CREATE INDEX IF NOT EXISTS "idx_audit_log_status_60fba5" ON "audit_log" ("status");
CREATE INDEX IF NOT EXISTS "idx_audit_log_respons_1e56a2" ON "audit_log" ("response_time");
CREATE INDEX IF NOT EXISTS "idx_audit_log_ip_addr_29e592" ON "audit_log" ("ip_address");
CREATE INDEX IF NOT EXISTS "idx_audit_log_user_ag_f560df" ON "audit_log" ("user_agent");
CREATE INDEX IF NOT EXISTS "idx_audit_log_operati_63093c" ON "audit_log" ("operation_type");
CREATE INDEX IF NOT EXISTS "idx_audit_log_log_lev_8860f6" ON "audit_log" ("log_level");
CREATE INDEX IF NOT EXISTS "idx_audit_log_is_dele_975c0e" ON "audit_log" ("is_deleted");
CREATE INDEX IF NOT EXISTS "idx_audit_log_created_554eed" ON "audit_log" ("created_at", "username");
CREATE INDEX IF NOT EXISTS "idx_audit_log_created_44d9e9" ON "audit_log" ("created_at", "module");
CREATE INDEX IF NOT EXISTS "idx_audit_log_created_85167c" ON "audit_log" ("created_at", "status");
CREATE INDEX IF NOT EXISTS "idx_audit_log_created_10447f" ON "audit_log" ("created_at", "operation_type");
CREATE INDEX IF NOT EXISTS "idx_audit_log_created_9d86a1" ON "audit_log" ("created_at", "log_level");
CREATE TABLE IF NOT EXISTS "rate_limit_bucket" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL /* Created at */,
    "updated_at" TIMESTAMP NOT NULL /* Updated at */,
    "bucket_key" VARCHAR(255) NOT NULL UNIQUE /* Rate-limit bucket key */,
    "count" INT NOT NULL /* Request count within window */,
    "expires_at" BIGINT NOT NULL /* Expiration timestamp */
);
CREATE INDEX IF NOT EXISTS "idx_rate_limit__bucket__ce63af" ON "rate_limit_bucket" ("bucket_key");
CREATE INDEX IF NOT EXISTS "idx_rate_limit__expires_eac77b" ON "rate_limit_bucket" ("expires_at");
CREATE TABLE IF NOT EXISTS "role" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL /* Created at */,
    "updated_at" TIMESTAMP NOT NULL /* Updated at */,
    "name" VARCHAR(20) NOT NULL UNIQUE /* Role name */,
    "desc" VARCHAR(500) /* Role description */,
    "menu_paths" JSON NOT NULL /* Menu permission paths */,
    "api_ids" JSON NOT NULL /* API permission ID list */
);
CREATE INDEX IF NOT EXISTS "idx_role_name_e5618b" ON "role" ("name");
CREATE TABLE IF NOT EXISTS "system_setting" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL /* Created at */,
    "updated_at" TIMESTAMP NOT NULL /* Updated at */,
    "key" VARCHAR(100) NOT NULL UNIQUE /* Setting key */,
    "value" JSON NOT NULL /* Setting value */,
    "description" VARCHAR(255) /* Setting description */
);
CREATE INDEX IF NOT EXISTS "idx_system_sett_key_ed06a3" ON "system_setting" ("key");
CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL /* ID */,
    "created_at" TIMESTAMP NOT NULL /* Created at */,
    "updated_at" TIMESTAMP NOT NULL /* Updated at */,
    "username" VARCHAR(20) NOT NULL UNIQUE /* Username */,
    "nickname" VARCHAR(30) /* Nickname */,
    "avatar" VARCHAR(500) /* Avatar URL */,
    "email" VARCHAR(255) UNIQUE /* Email */,
    "phone" VARCHAR(20) /* Phone */,
    "password" VARCHAR(128) /* Password */,
    "is_active" INT NOT NULL /* Active flag */,
    "is_superuser" INT NOT NULL /* Superuser flag */,
    "last_login" TIMESTAMP /* Last login time */,
    "session_version" INT NOT NULL /* Session version */,
    "refresh_token_jti" VARCHAR(32) /* Current refresh token identifier */
);
CREATE INDEX IF NOT EXISTS "idx_user_usernam_9987ab" ON "user" ("username");
CREATE INDEX IF NOT EXISTS "idx_user_nicknam_579938" ON "user" ("nickname");
CREATE INDEX IF NOT EXISTS "idx_user_email_1b4f1c" ON "user" ("email");
CREATE INDEX IF NOT EXISTS "idx_user_phone_4e3ecc" ON "user" ("phone");
CREATE INDEX IF NOT EXISTS "idx_user_is_acti_83722a" ON "user" ("is_active");
CREATE INDEX IF NOT EXISTS "idx_user_is_supe_b8a218" ON "user" ("is_superuser");
CREATE INDEX IF NOT EXISTS "idx_user_last_lo_af118a" ON "user" ("last_login");
CREATE INDEX IF NOT EXISTS "idx_user_session_c59d2d" ON "user" ("session_version");
CREATE INDEX IF NOT EXISTS "idx_user_refresh_dc1daf" ON "user" ("refresh_token_jti");
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);
CREATE TABLE IF NOT EXISTS "user_role" (
    "user_id" INT NOT NULL REFERENCES "user" ("id") ON DELETE CASCADE,
    "role_id" INT NOT NULL REFERENCES "role" ("id") ON DELETE CASCADE
);
CREATE UNIQUE INDEX IF NOT EXISTS "uidx_user_role_user_id_d0bad3" ON "user_role" ("user_id", "role_id");"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """


MODELS_STATE = (
    "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"
)
