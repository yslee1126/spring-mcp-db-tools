"""
Datasource listing tool.
Provides functionality to list configured datasources.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_spring_db_tools.common.yaml_parser import DataSourceConfig


def list_datasources(datasources: list["DataSourceConfig"]) -> str:
    """
    List all configured datasources.
    
    Args:
        datasources: List of DataSourceConfig objects
        
    Returns:
        Formatted string with datasource information
    """
    lines = [
        "=" * 60,
        "CONFIGURED DATASOURCES",
        "=" * 60,
        ""
    ]
    
    for i, ds in enumerate(datasources, 1):
        lines.append(f"{i}. {ds.name}")
        lines.append(f"   Type: {ds.db_type}")
        lines.append(f"   Database: {ds.database}")
        lines.append(f"   Host: {ds.host}:{ds.port}")
        lines.append(f"   URL: {ds.url}")
        lines.append("")
    
    lines.append(f"Total: {len(datasources)} datasource(s)")
    return "\n".join(lines)


def get_datasource_summary(datasources: list["DataSourceConfig"]) -> dict:
    """
    Get a summary of configured datasources.
    
    Args:
        datasources: List of DataSourceConfig objects
        
    Returns:
        Dictionary with datasource summary
    """
    return {
        'count': len(datasources),
        'datasources': [
            {
                'name': ds.name,
                'type': ds.db_type,
                'database': ds.database,
                'host': ds.host,
                'port': ds.port
            }
            for ds in datasources
        ]
    }
