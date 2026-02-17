"""
View information tool.
Provides database view inspection functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_spring_db_tools.utils.db_connector import DatabaseConnector


def get_views(connector: "DatabaseConnector", view_name: str = "") -> dict:
    """
    Get views information from the database.
    
    Args:
        connector: Database connector instance
        view_name: Optional specific view name to query
        
    Returns:
        Dictionary containing views information
    """
    with connector.connection_context():
        return connector.get_views_info(view_name)


def format_views_info(ds_name: str, view_info: dict) -> str:
    """
    Format views information for display.
    
    Args:
        ds_name: Datasource name
        view_info: Views information dictionary
        
    Returns:
        Formatted string representation
    """
    lines = [
        "=" * 70,
        f"DATABASE VIEWS: {ds_name}",
        f"Database: {view_info.get('database', 'N/A')}",
        "=" * 70,
        ""
    ]
    
    views = view_info.get('views', [])
    if not views:
        lines.append("No views found.")
        return "\n".join(lines)
        
    for view in views:
        schema_prefix = f"{view['schema']}." if view.get('schema') else ""
        view_name = f"{schema_prefix}{view['name']}"
        
        lines.append(f"👁️ VIEW: {view_name}")
        
        if view.get('definition'):
            lines.append("   Definition:")
            lines.append("   " + "-" * 60)
            def_lines = view['definition'].split('\n')
            for line in def_lines:
                lines.append(f"   | {line}")
            lines.append("   " + "-" * 60)
            
        lines.append("")
    
    lines.append(f"Total Views: {len(views)}")
    return "\n".join(lines)
