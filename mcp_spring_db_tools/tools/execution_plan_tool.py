"""
Execution plan tool.
Provides SQL query execution plan analysis functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_spring_db_tools.common.db_connector import DatabaseConnector


# Allowed query types for execution plan
ALLOWED_QUERY_STARTS = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH')


def validate_query(query: str) -> tuple[bool, str]:
    """
    Validate that the query is allowed for execution plan analysis.
    
    Args:
        query: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    query_upper = query.strip().upper()
    
    if not any(query_upper.startswith(start) for start in ALLOWED_QUERY_STARTS):
        return False, (
            "Error: Only SELECT, INSERT, UPDATE, DELETE, and WITH queries are allowed. "
            "DDL statements (CREATE, DROP, ALTER, TRUNCATE) are not permitted for EXPLAIN."
        )
    
    return True, ""


def get_execution_plan(connector: "DatabaseConnector", query: str) -> str:
    """
    Get execution plan for a SQL query.
    
    Args:
        connector: Database connector instance
        query: SQL query to analyze
        
    Returns:
        Execution plan as formatted string
    """
    # Validate query
    is_valid, error_message = validate_query(query)
    if not is_valid:
        return error_message
    
    with connector.connection_context():
        return connector.get_execution_plan(query)


def format_execution_plan_result(ds_name: str, query: str, plan: str) -> str:
    """
    Format execution plan result with metadata.
    
    Args:
        ds_name: Datasource name
        query: Original SQL query
        plan: Execution plan string
        
    Returns:
        Formatted result string
    """
    query_preview = query[:200] + '...' if len(query) > 200 else query
    
    return "\n".join([
        f"Datasource: {ds_name}",
        f"Query: {query_preview}",
        "",
        plan
    ])
