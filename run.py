import os

from app import create_app
from config import DevelopmentConfig, ProductionConfig

app = create_app(ProductionConfig() if os.environ.get("APP_ENV") == "production" else DevelopmentConfig)

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000)
