"""
Stored procedure information tool.
Provides database stored procedure inspection functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_spring_db_tools.utils.db_connector import DatabaseConnector


def get_procedures(connector: "DatabaseConnector", procedure_name: str = "") -> dict:
    """
    Get stored procedures information from the database.
    
    Args:
        connector: Database connector instance
        procedure_name: Optional specific procedure name to query
        
    Returns:
        Dictionary containing stored procedures information
    """
    with connector.connection_context():
        return connector.get_procedures_info(procedure_name)


def format_procedures_info(ds_name: str, proc_info: dict) -> str:
    """
    Format stored procedures information for display.
    
    Args:
        ds_name: Datasource name
        proc_info: Procedures information dictionary
        
    Returns:
        Formatted string representation
    """
    lines = [
        "=" * 70,
        f"STORED PROCEDURES: {ds_name}",
        f"Database: {proc_info.get('database', 'N/A')}",
        "=" * 70,
        ""
    ]
    
    procedures = proc_info.get('procedures', [])
    if not procedures:
        lines.append("No stored procedures found.")
        return "\n".join(lines)
        
    for proc in procedures:
        schema_prefix = f"{proc['schema']}." if proc.get('schema') else ""
        proc_name = f"{schema_prefix}{proc['name']}"
        
        lines.append(f"📦 PROCEDURE: {proc_name}")
        if proc.get('comment'):
            lines.append(f"   Comment: {proc['comment']}")
            
        # Definition
        if proc.get('definition'):
            lines.append("   Definition:")
            lines.append("   " + "-" * 60)
            def_lines = proc['definition'].split('\n')
            # Indent definition
            for line in def_lines:
                lines.append(f"   | {line}")
            lines.append("   " + "-" * 60)
            
        lines.append("")
    
    lines.append(f"Total Procedures: {len(procedures)}")
    return "\n".join(lines)
