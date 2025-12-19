from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Database connection URL
# Using the URI from the connected MCP server: postgresql://admin:348150@localhost:5435/sskedata
DATABASE_URL = os.environ.get('DATABASE_URL')

# Create a SQLAlchemy engine
engine = create_engine(DATABASE_URL)

# Create a configured "Session" class
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create a declarative base object
Base = declarative_base(metadata=MetaData(schema="sskedata"))

# Dependency to get a database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Import models here so that Base has them before being imported by Alembic
# from . import models
