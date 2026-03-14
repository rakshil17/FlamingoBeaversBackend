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
    flask_host: str
    flask_port: int
    flask_debug: bool

    elastic_host: str
    elastic_api_key: str
    elastic_index: str


settings = Settings(
    flask_host=os.getenv("FLASK_HOST", "0.0.0.0"),
    flask_port=int(os.getenv("FLASK_PORT", "5004")),
    flask_debug=_as_bool(os.getenv("FLASK_DEBUG"), default=True),
    elastic_host=os.getenv("ELASTIC_HOST", "http://localhost:9200"),
    elastic_api_key=os.getenv("ELASTIC_API_KEY", ""),
    elastic_index=os.getenv("ELASTIC_INDEX", "university-courses"),
)
