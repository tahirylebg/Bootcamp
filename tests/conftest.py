import os

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://user:pass@localhost:5432/testdb")
os.environ.setdefault("AI_PROVIDER", "mock")
