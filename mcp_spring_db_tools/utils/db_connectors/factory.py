from .base import DatabaseConnector
from .mysql import MySQLConnector
from .postgresql import PostgreSQLConnector
from .mssql import MSSQLConnector
from .sqlite import SQLiteConnector
from .h2 import H2Connector
from ..yaml_parser import DataSourceConfig


def create_connector(config: DataSourceConfig) -> DatabaseConnector:
    """
    Factory function to create the appropriate database connector.
    
    Args:
        config: DataSourceConfig with connection details
        
    Returns:
        Appropriate DatabaseConnector subclass instance
        
    Raises:
        ValueError: If database type is not supported
    """
    connectors = {
        'mysql': MySQLConnector,
        'mariadb': MySQLConnector,  # MariaDB uses MySQL protocol
        'postgresql': PostgreSQLConnector,
        'h2': H2Connector,
        'sqlserver': MSSQLConnector,
        'sqlite': SQLiteConnector,
    }
    
    connector_class = connectors.get(config.db_type)
    if not connector_class:
        raise ValueError(f"Unsupported database type: {config.db_type}")
    
    return connector_class(config)
