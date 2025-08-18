# afiacare_SE_Project

## Overview

This project repository (`afiacare_SE_Project`) is dedicated to the development of a web application aimed at enhancing healthcare management. It utilizes FastAPI for building APIs, SQLAlchemy for database interactions, and Pydantic for data validation.

## Structure

### `db`

This directory houses the database connection instance, database configuration file, and shared authentication verification.

### `endpoints`

All API endpoints are defined within this directory.

### `models`

The `models` directory contains definitions for all database models (tables) used in the application.

### `schemas`

Here, Pydantic schemas are defined to validate data against predefined structures.

## Usage

After cloning the repository, follow these steps:

1. Switch to the `dev` branch.
2. Create a virtual environment if not already present:
   - For Linux/MacOS: `python3 -m venv venv` and activate it using `source venv/bin/activate`
   - For Windows: `python -m venv venv` and activate it using `venv\Scripts\activate`
3. Install dependencies from `requirements.txt`:
   ```
   pip install -r requirements.txt
   ```
4. Run the application using Uvicorn:
   ```
   uvicorn main:app --reload
   ```
5. Ensure you have a `.env` file configured with necessary credentials for the application.
