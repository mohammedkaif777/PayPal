from app.core.config import get_settings
from app.core.logging import configure_logging
from app.db.init_db import init_db


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    init_db()
    print("Database initialized and API keys seeded.")
    print("Roles: admin, operator, reviewer, read_only")
    print("API keys are read from environment variables or .env.")


if __name__ == "__main__":
    main()
