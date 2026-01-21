from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Connection string for local Docker PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:localpassword123@127.0.0.1:5433/photoflow_db"

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()