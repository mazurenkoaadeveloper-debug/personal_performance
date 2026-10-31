import os
from urllib.parse import quote


def main() -> None:
    password = quote(os.environ["POSTGRES_PASSWORD"], safe="")
    print(f"postgresql+asyncpg://activity:{password}@postgres:5432/activity")


if __name__ == "__main__":
    main()
