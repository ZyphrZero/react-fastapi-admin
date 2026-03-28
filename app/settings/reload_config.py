"""
Hot-reload configuration module.
Defines the directories and file patterns ignored by Granian hot reload.
"""

# Ignored directory list.
RELOAD_IGNORE_DIRS = [
    "logs",  # Ignore log directories.
    "storage",  # Ignore storage directories.
    "__pycache__",  # Ignore Python caches.
    ".git",  # Ignore the git directory.
    "node_modules",  # Ignore node_modules.
    "migrations",  # Ignore database migrations.
    ".pytest_cache",  # Ignore pytest caches.
    ".venv",  # Ignore virtual environments.
    "venv",  # Ignore virtual environments.
    "env",  # Ignore environment directories.
    ".mypy_cache",  # Ignore mypy caches.
    ".ruff_cache",  # Ignore ruff caches.
    "dist",  # Ignore build distribution output.
    "build",  # Ignore build directories.
    ".coverage",  # Ignore coverage data files.
    "htmlcov",  # Ignore coverage report directories.
    "tests",  # Ignore test directories.
    "logs",  # Ignore log directories.
]

# Ignored file patterns (regular expressions).
RELOAD_IGNORE_PATTERNS = [
    # Log files.
    r".*\.log$",
    r".*\.log\.\d+$",
    # Database files.
    r".*\.sqlite3.*",
    r".*\.db$",
    r".*\.db-.*$",
    # Python-related files.
    r".*\.pyc$",
    r".*\.pyo$",
    r".*\.pyd$",
    # Temporary files.
    r".*\.tmp$",
    r".*\.temp$",
    r".*\.swp$",
    r".*\.swo$",
    r".*~$",
    # System files.
    r".*\.DS_Store$",
    r".*Thumbs\.db$",
    r".*\.directory$",
    # Editor files.
    r".*\.vscode.*",
    r".*\.idea.*",
    # Tests and coverage artifacts.
    r".*\.coverage$",
    r".*\.pytest_cache.*",
    # Build artifacts.
    r".*\.egg-info.*",
    r".*\.wheel$",
    r".*\.whl$",
    # Version-control files.
    r".*\.git.*",
    r".*\.gitignore$",
    r".*\.gitkeep$",
    # Backup configuration files.
    r".*\.bak$",
    r".*\.backup$",
    r".*\.orig$",
    # Lock and PID files.
    r".*\.lock$",
    r".*\.pid$",
]

# Watched paths. Only application code is monitored.
RELOAD_WATCH_PATHS = [
    "app",  # Main application directory.
]

# Hot-reload configuration.
RELOAD_CONFIG = {
    "reload_ignore_dirs": RELOAD_IGNORE_DIRS,
    "reload_ignore_patterns": RELOAD_IGNORE_PATTERNS,
    "reload_paths": RELOAD_WATCH_PATHS,
    "reload_tick": 100,  # Watch interval in milliseconds.
}
