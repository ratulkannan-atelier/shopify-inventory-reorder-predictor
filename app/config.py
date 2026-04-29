import os


class Config:
    SQLALCHEMY_DATABASE_URI: str = os.environ.get(
        "DATABASE_URL",
        "postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}".format(
            user=os.environ.get("POSTGRES_USER", "reorder_user"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=os.environ.get("POSTGRES_PORT", "5432"),
            db=os.environ.get("POSTGRES_DB", "reorder_predictor"),
        ),
    )
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False
