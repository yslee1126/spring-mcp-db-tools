"""
Database connector module.
Provides connections and query execution for various database types.
This is a backward-compatible wrapper for the refactored db_connectors package.
"""

from .db_connectors.base import DatabaseConnector
from .db_connectors.mysql import MySQLConnector
from .db_connectors.postgresql import PostgreSQLConnector
from .db_connectors.mssql import MSSQLConnector
from .db_connectors.sqlite import SQLiteConnector
from .db_connectors.h2 import H2Connector
from .db_connectors.factory import create_connector

# Re-exporting for backward compatibility
__all__ = [
    'DatabaseConnector',
    'MySQLConnector',
    'PostgreSQLConnector',
    'MSSQLConnector',
    'SQLiteConnector',
    'H2Connector',
    'create_connector'
]
