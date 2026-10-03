"""
Command Line Interface (CLI) for the LearnEnglish Application.

This module provides a CLI for managing the LearnEnglish application,
including database operations. The CLI is built using Click and supports:

- Database initialization and schema creation

Usage examples:
    # Initialize the database (create DB + all tables)
    $ python cli.py database init

For detailed help on each command, use:
    $ python cli.py [command] --help
"""

import click
import psycopg2
from psycopg2 import sql

from app.config.settings import Database
from app.database.async_db import get_engine
from app.database.model import Base
from app.features.conversation import model as _conversation_model
from app.features.dictionary import model as _dictionary_model
from app.features.engagement import model as _engagement_model
from app.features.feedback import model as _feedback_model
from app.features.lesson import model as _lesson_model
from app.features.notifications import model as _notification_model
from app.features.preferences import model as _preferences_model
from app.features.review import model as _review_model
from app.features.token import model as _token_model
from app.features.user import model as _user_model
from app.features.vocabulary import model as _vocabulary_model
from app.features.wordlist import model as _wordlist_model

db = Database()


@click.group()
def learn_english_cli():
    """Command-line interface for LearnEnglish."""
    pass


@learn_english_cli.group("database")
def learn_english_database():
    """Commands for managing the LearnEnglish database."""
    click.secho(
        f"Connecting to database '{db.db_name}' at {db.db_host}:{db.db_port}...",
        fg="yellow",
    )


@learn_english_database.command("init")
def init_database():
    """Creates the database and initializes all tables."""
    # Step 1: Create the database if it doesn't exist
    try:
        conn = psycopg2.connect(
            host=db.db_host,
            user=db.db_user,
            password=db.db_password,
            port=int(db.db_port or 5432),
            database="postgres",
        )
        conn.autocommit = True
        with conn.cursor() as cursor:
            cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s;", (db.db_name,))
            exists = cursor.fetchone()
            if not exists:
                cursor.execute(
                    sql.SQL("CREATE DATABASE {};").format(sql.Identifier(db.db_name))
                )
                click.secho(f"Database '{db.db_name}' created.", fg="green")
            else:
                click.secho(f"Database '{db.db_name}' already exists.", fg="green")
        conn.close()
        click.secho(f"Database '{db.db_name}' is ready.", fg="green")
    except Exception as e:
        click.secho(f"ERROR creating database: {e}", fg="red", bold=True)
        return

    # Step 2: Create all tables from the model metadata
    try:
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        click.secho("All tables created successfully.", fg="green")
    except Exception as e:
        click.secho(f"ERROR creating tables: {e}", fg="red", bold=True)
        return

    click.secho("Database initialization completed!", fg="green", bold=True)


def entrypoint():
    """The entry point that the CLI is executed from."""
    try:
        learn_english_cli()
    except Exception as e:
        click.secho(f"ERROR: {e}", bold=True, fg="red")


if __name__ == "__main__":
    entrypoint()
