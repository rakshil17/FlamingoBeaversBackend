import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv


load_dotenv()


def _as_bool(value: Optional[str], default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    flask_env: str
    flask_debug: bool
    flask_host: str
    flask_port: int

    elastic_host: str
    elastic_index: str
    elastic_username: str | None
    elastic_password: str | None
    elastic_verify_certs: bool


settings = Settings(
    flask_env=os.getenv("FLASK_ENV", "development"),
    flask_debug=_as_bool(os.getenv("FLASK_DEBUG"), default=True),
    flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
    flask_port=int(os.getenv("FLASK_PORT", "5000")),
    elastic_host=os.getenv("ELASTIC_HOST", "http://localhost:9200"),
    elastic_index=os.getenv("ELASTIC_INDEX", "flamingo-beavers"),
    elastic_username=os.getenv("ELASTIC_USERNAME") or None,
    elastic_password=os.getenv("ELASTIC_PASSWORD") or None,
    elastic_verify_certs=_as_bool(
        os.getenv("ELASTIC_VERIFY_CERTS"),
        default=False,
    ),
)
