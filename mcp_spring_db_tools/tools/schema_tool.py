"""
Schema information tool.
Provides database schema inspection functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_spring_db_tools.common.db_connector import DatabaseConnector


def get_schema_info(connector: "DatabaseConnector", table_name: str = "") -> dict:
    """
    Get schema information from the database.
    
    Args:
        connector: Database connector instance
        table_name: Optional specific table name to query
        
    Returns:
        Dictionary containing schema information
    """
    with connector.connection_context():
        return connector.get_schema_info(table_name)


def format_schema_info(ds_name: str, schema_info: dict) -> str:
    """
    Format schema information for display.
    
    Args:
        ds_name: Datasource name
        schema_info: Schema information dictionary
        
    Returns:
        Formatted string representation
    """
    lines = [
        "=" * 70,
        f"DATABASE SCHEMA: {ds_name}",
        f"Database: {schema_info.get('database', 'N/A')}",
        "=" * 70,
        ""
    ]
    
    for table in schema_info.get('tables', []):
        # Display schema.table if schema is available
        table_display_name = f"{table['schema']}.{table['name']}" if table.get('schema') else table['name']
        lines.append(f"📋 TABLE: {table_display_name}")
        if table.get('comment'):
            lines.append(f"   Comment: {table['comment']}")
        if table.get('estimated_rows'):
            lines.append(f"   Estimated Rows: {table['estimated_rows']:,}")
        if table.get('engine'):
            lines.append(f"   Engine: {table['engine']}")
        lines.append("")
        
        # Columns
        lines.append("   COLUMNS:")
        lines.append("   " + "-" * 60)
        for col in table.get('columns', []):
            nullable = "NULL" if col.get('nullable') else "NOT NULL"
            key_info = f" [{col['key']}]" if col.get('key') else ""
            default_info = f" DEFAULT {col['default']}" if col.get('default') else ""
            extra_info = f" {col['extra']}" if col.get('extra') else ""
            comment_info = f" -- {col['comment']}" if col.get('comment') else ""
            
            lines.append(
                f"   • {col['name']}: {col['type']} {nullable}{key_info}{default_info}{extra_info}{comment_info}"
            )
        lines.append("")
        
        # Indexes
        if table.get('indexes'):
            lines.append("   INDEXES:")
            lines.append("   " + "-" * 60)
            for idx in table['indexes']:
                unique = "UNIQUE " if idx.get('unique') else ""
                idx_type = f" ({idx['type']})" if idx.get('type') else ""
                columns = ", ".join(idx.get('columns', []))
                lines.append(f"   • {unique}{idx['name']}: [{columns}]{idx_type}")
            lines.append("")
        
        # Foreign Keys
        if table.get('foreign_keys'):
            lines.append("   FOREIGN KEYS:")
            lines.append("   " + "-" * 60)
            for fk in table['foreign_keys']:
                lines.append(
                    f"   • {fk['name']}: {fk['column']} -> {fk['referenced_table']}.{fk['referenced_column']}"
                )
            lines.append("")
        
        lines.append("")
    
    lines.append(f"Total Tables: {len(schema_info.get('tables', []))}")
    return "\n".join(lines)
