import secrets
from pathlib import Path
from typing import List, Optional

from pydantic import Field, computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def get_root_path() -> Path:
    """Return the project root path."""
    return Path(__file__).parent.parent.parent.resolve()


def ensure_path(path: str, create_parent: bool = True) -> Path:
    """
    Build a project-relative path with cross-platform pathlib handling.

    Args:
        path: Relative path.
        create_parent: Whether to create the parent directory. Defaults to True.
    """
    root = get_root_path()
    full_path = root / path
    if create_parent:
        full_path.parent.mkdir(parents=True, exist_ok=True)
    return full_path


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore")

    # Core application settings.
    APP_ENV: str = Field(default="dev", description="应用环境（dev/prod）")
    VERSION: str = Field(default="0.1.0", description="应用版本")
    APP_TITLE: str = Field(default="React FastAPI Admin", description="应用标题")
    PROJECT_NAME: str = Field(default="React FastAPI Admin", description="项目名称")
    APP_DESCRIPTION: str = Field(default="React FastAPI Admin Description", description="应用描述")
    DEBUG: bool = Field(default=False, description="调试模式")
    LOGIN_PAGE_IMAGE_URL: str = Field(default="", description="登录页展示图片地址")
    LOGIN_PAGE_IMAGE_MODE: str = Field(default="contain", description="登录页图片显示模式")
    NOTIFICATION_POSITION: str = Field(default="top-right", description="前端通知显示位置")
    NOTIFICATION_DURATION: int = Field(default=4000, description="前端通知显示时长（毫秒）")
    NOTIFICATION_VISIBLE_TOASTS: int = Field(default=3, description="前端同时显示通知数量")
    HOST: str = Field(default="0.0.0.0", description="服务监听地址")
    PORT: int = Field(default=9999, description="服务监听端口")
    SERVER_RELOAD: Optional[bool] = Field(default=None, description="是否启用服务热重载")

    # CORS settings.
    CORS_ORIGINS: List[str] = Field(default=["*"], description="CORS 允许的来源")
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True, description="CORS 允许凭证")
    CORS_ALLOW_METHODS: List[str] = Field(default=["*"], description="CORS 允许的方法")
    CORS_ALLOW_HEADERS: List[str] = Field(default=["*"], description="CORS 允许的头部")

    # Path settings.
    BASE_DIR: Path = Field(default_factory=get_root_path, description="项目根目录")
    LOGS_ROOT: str = Field(default="app/logs", description="日志目录")

    # Logging settings.
    LOG_RETENTION_DAYS: int = Field(default=7, description="日志保留天数")
    LOG_ROTATION: str = Field(default="1 day", description="日志轮转周期")
    LOG_MAX_FILE_SIZE: str = Field(default="10 MB", description="单个日志文件最大大小")
    LOG_ENABLE_ACCESS_LOG: bool = Field(default=True, description="是否启用访问日志")

    # Security settings.
    SECRET_KEY: str = Field(default="", description="应用密钥")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT 算法")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, description="JWT 访问令牌过期时间（分钟）")
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="JWT 刷新令牌过期时间（天）")
    JWT_AUDIENCE: str = Field(default="react-fastapi-admin", description="JWT 受众")
    JWT_ISSUER: str = Field(default="react-fastapi-admin", description="JWT 签发者")
    REFRESH_TOKEN_COOKIE_NAME: str = Field(default="refresh_token", description="刷新令牌 Cookie 名称")
    REFRESH_TOKEN_COOKIE_SECURE: Optional[bool] = Field(default=None, description="刷新令牌 Cookie 是否仅限 HTTPS")
    REFRESH_TOKEN_COOKIE_SAMESITE: str = Field(default="lax", description="刷新令牌 Cookie SameSite 策略")

    # IP allowlist settings.
    IP_WHITELIST: str = Field(default="", description="IP 白名单字符串")
    TRUST_PROXY_HEADERS: bool = Field(default=False, description="是否信任代理请求头中的客户端 IP")
    TRUSTED_PROXY_IPS: str = Field(default="", description="可信代理 IP 列表，逗号分隔")

    # Rate-limit settings.
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="是否启用请求频率限制")
    RATE_LIMIT_MAX_REQUESTS: int = Field(default=60, description="时间窗口内最大请求数")
    RATE_LIMIT_WINDOW_SECONDS: int = Field(default=60, description="时间窗口大小（秒）")

    # Password policy settings.
    PASSWORD_MIN_LENGTH: int = Field(default=8, description="密码最小长度")
    PASSWORD_REQUIRE_UPPERCASE: bool = Field(default=True, description="是否要求包含大写字母")
    PASSWORD_REQUIRE_LOWERCASE: bool = Field(default=True, description="是否要求包含小写字母")
    PASSWORD_REQUIRE_DIGITS: bool = Field(default=True, description="是否要求包含数字")
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True, description="是否要求包含特殊字符")

    # Initial administrator settings.
    INITIAL_ADMIN_USERNAME: str = Field(default="admin", description="初始管理员用户名")
    INITIAL_ADMIN_EMAIL: str = Field(default="admin@example.com", description="初始管理员邮箱")
    INITIAL_ADMIN_NICKNAME: str = Field(default="admin", description="初始管理员昵称")
    INITIAL_ADMIN_PASSWORD: str = Field(default="", description="初始管理员密码，留空时首次引导自动生成")

    # Database settings.
    DB_CONNECTION: str = Field(default="sqlite", description="数据库连接类型")
    DB_FILE: str = Field(default="db.sqlite3", description="SQLite 数据库文件名")

    # MySQL/PostgreSQL settings.
    DB_HOST: str = Field(default="localhost", description="数据库主机")
    DB_PORT: int = Field(default=3306, description="数据库端口")
    DB_USERNAME: str = Field(default="root", description="数据库用户名")
    DB_PASSWORD: str = Field(default="", description="数据库密码")
    DB_DATABASE: str = Field(default="fastapi_admin", description="数据库名称")

    # Date and time formatting.
    DATETIME_FORMAT: str = Field(default="%Y-%m-%d %H:%M:%S", description="日期时间格式")

    @field_validator(
        "APP_ENV",
        "SERVER_RELOAD",
        "REFRESH_TOKEN_COOKIE_SECURE",
        mode="before",
    )
    @classmethod
    def normalize_settings_inputs(cls, value: object, info) -> object:
        """Normalize setting inputs before standard validation."""
        if info.field_name == "APP_ENV":
            if not isinstance(value, str):
                raise ValueError("APP_ENV 必须为 dev 或 prod")

            normalized = value.strip().lower()
            if normalized not in {"dev", "prod"}:
                raise ValueError("APP_ENV 仅支持 dev 或 prod")
            return normalized

        if isinstance(value, str):
            value = value.strip()
            if not value:
                return None
        return value

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        insecure_secret_keys = {
            "",
            "3488a63e1765035d386f05409663f55c83bfae3b3c61a932744b20ad14244dcf",
            "your_production_secret_key",
        }

        if self.SECRET_KEY in insecure_secret_keys:
            if self.is_development:
                self.SECRET_KEY = secrets.token_hex(32)
            else:
                raise ValueError("生产环境必须显式配置安全的 SECRET_KEY")

        if len(self.SECRET_KEY) < 32:
            raise ValueError("SECRET_KEY 长度不能少于 32 个字符")

        if self.is_production and self.DEBUG:
            raise ValueError("生产环境必须关闭 DEBUG")

        if self.JWT_ALGORITHM.lower() == "none":
            raise ValueError("JWT_ALGORITHM 不能为 none")

        allowed_same_site_values = {"lax", "strict", "none"}
        if self.REFRESH_TOKEN_COOKIE_SAMESITE.lower() not in allowed_same_site_values:
            raise ValueError("REFRESH_TOKEN_COOKIE_SAMESITE 必须为 lax、strict 或 none")
        self.REFRESH_TOKEN_COOKIE_SAMESITE = self.REFRESH_TOKEN_COOKIE_SAMESITE.lower()

        if self.TRUST_PROXY_HEADERS and not self.trusted_proxy_ips:
            raise ValueError("启用 TRUST_PROXY_HEADERS 时必须显式配置 TRUSTED_PROXY_IPS")

        return self

    @computed_field
    @property
    def logs_path(self) -> Path:
        """Return the log directory path."""
        return ensure_path(self.LOGS_ROOT)

    @computed_field
    @property
    def storage_root_path(self) -> Path:
        """Return the static storage root path without creating it automatically."""
        return ensure_path("storage", create_parent=False)

    @computed_field
    @property
    def ip_whitelist(self) -> List[str]:
        """Return the IP allowlist."""
        if not self.IP_WHITELIST:
            return []
        return [ip.strip() for ip in self.IP_WHITELIST.split(",") if ip.strip()]

    @computed_field
    @property
    def trusted_proxy_ips(self) -> List[str]:
        """Return the trusted proxy IP list."""
        if not self.TRUSTED_PROXY_IPS:
            return []
        return [ip.strip() for ip in self.TRUSTED_PROXY_IPS.split(",") if ip.strip()]

    @computed_field
    @property
    def is_production(self) -> bool:
        """Return whether the current environment is production."""
        return self.APP_ENV == "prod"

    @computed_field
    @property
    def is_development(self) -> bool:
        """Return whether the current environment is development."""
        return self.APP_ENV == "dev"

    @computed_field
    @property
    def server_reload_enabled(self) -> bool:
        """Return whether hot reload should be enabled for the current environment and settings."""
        if self.SERVER_RELOAD is not None:
            return self.SERVER_RELOAD
        return self.is_development

    @computed_field
    @property
    def refresh_token_cookie_secure(self) -> bool:
        """Return whether the refresh-token cookie should be HTTPS-only."""
        if self.REFRESH_TOKEN_COOKIE_SECURE is not None:
            return self.REFRESH_TOKEN_COOKIE_SECURE
        return self.is_production

    @computed_field
    @property
    def tortoise_orm(self) -> dict:
        """Build the Tortoise ORM configuration dynamically."""
        base_config = {
            "connections": {
                "sqlite": {
                    "engine": "tortoise.backends.sqlite",
                    "credentials": {"file_path": str(self.BASE_DIR / self.DB_FILE)},
                },
            },
            "apps": {
                "models": {
                    "models": ["app.models", "aerich.models"],
                    "default_connection": self.DB_CONNECTION,
                },
            },
            "use_tz": False,
            "timezone": "Asia/Shanghai",
        }

        # Add the matching database configuration for the selected connection type.
        if self.DB_CONNECTION == "mysql":
            base_config["connections"]["mysql"] = {
                "engine": "tortoise.backends.mysql",
                "credentials": {
                    "host": self.DB_HOST,
                    "port": self.DB_PORT,
                    "user": self.DB_USERNAME,
                    "password": self.DB_PASSWORD,
                    "database": self.DB_DATABASE,
                },
            }
        elif self.DB_CONNECTION == "postgres":
            base_config["connections"]["postgres"] = {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": self.DB_HOST,
                    "port": self.DB_PORT,
                    "user": self.DB_USERNAME,
                    "password": self.DB_PASSWORD,
                    "database": self.DB_DATABASE,
                },
            }

        return base_config

    def model_post_init(self, __context) -> None:
        """Post-initialization processing for the settings model."""
        # Ensure the log directory exists. This is required.
        self.logs_path.mkdir(parents=True, exist_ok=True)
        # Note: the storage directory is created only when it is actually needed, not during startup.

    def get_database_url(self) -> str:
        """Return the database connection URL."""
        if self.DB_CONNECTION == "sqlite":
            return f"sqlite:///{self.BASE_DIR / self.DB_FILE}"
        elif self.DB_CONNECTION == "mysql":
            return f"mysql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"
        elif self.DB_CONNECTION == "postgres":
            return (
                f"postgresql://{self.DB_USERNAME}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_DATABASE}"
            )
        else:
            raise ValueError(f"不支持的数据库类型: {self.DB_CONNECTION}")

    def __repr__(self) -> str:
        return f"<Settings env={self.APP_ENV} debug={self.DEBUG} db={self.DB_CONNECTION}>"


# Global settings instance.
settings = Settings()


# Print the current runtime information.
def print_startup_info():
    """Print startup information."""
    print(f"🚀 Runtime environment: {settings.APP_ENV}")
    print(f"🔧 Debug mode: {settings.DEBUG}")
    print(f"💾 Database connection: {settings.DB_CONNECTION}")
    if settings.DB_CONNECTION == "sqlite":
        print(f"📁 SQLite database file: {settings.DB_FILE}")
    print(f"📂 Project root path: {settings.BASE_DIR}")
    print(f"📋 Log path: {settings.logs_path}")
    print(f"💾 Static storage root path: {settings.storage_root_path}")
    if settings.ip_whitelist:
        print(f"🛡️  IP allowlist: {settings.ip_whitelist}")
    print("=" * 50)


# Print startup information when the module is executed directly.
if __name__ == "__main__":
    print_startup_info()
