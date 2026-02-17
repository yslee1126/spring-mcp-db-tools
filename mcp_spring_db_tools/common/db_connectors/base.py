from abc import ABC, abstractmethod
from typing import Any
from contextlib import contextmanager

from ..yaml_parser import DataSourceConfig


class DatabaseConnector(ABC):
    """Abstract base class for database connectors."""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._connection = None
    
    @abstractmethod
    def connect(self):
        """Establish a database connection."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close the database connection."""
        pass
    
    @abstractmethod
    def get_schema_info(self, table_name: str = "") -> dict:
        """
        Get database schema information including tables, columns, and indexes.
        
        Args:
            table_name: Optional specific table name to query (supports wildcards)
            
        Returns:
            Dictionary containing schema information
        """
        pass
    
    @abstractmethod
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """
        Get stored procedures information.
        
        Args:
            procedure_name: Optional specific procedure name to query
            
        Returns:
            Dictionary containing stored procedures information
        """
        pass

    @abstractmethod
    def get_views_info(self, view_name: str = "") -> dict:
        """
        Get views information.
        
        Args:
            view_name: Optional specific view name to query
            
        Returns:
            Dictionary containing views information
        """
        pass

    @abstractmethod
    def get_execution_plan(self, query: str) -> str:
        """
        Get the execution plan for a SQL query.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Execution plan as a formatted string
        """
        pass
    
    @contextmanager
    def connection_context(self):
        """Context manager for database connections."""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()
