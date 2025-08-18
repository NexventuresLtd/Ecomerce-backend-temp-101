from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Function to force recreate tables using CASCADE in PostgreSQL
def recreate_tables():
    with engine.connect() as connection:
        # Drop all tables with CASCADE (force drop foreign key constraints and dependent objects)
        connection.execute(text('DROP SCHEMA public CASCADE;'))
        
        # Recreate the schema (public is the default schema in PostgreSQL)
        connection.execute(text('CREATE SCHEMA public;'))

        # Recreate all tables
        Base.metadata.create_all(bind=engine)

# Example call to recreate tables
recreate_tables()
