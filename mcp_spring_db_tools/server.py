"""
MCP Server for Spring Boot Database Tools.

Provides database schema inspection and query execution plan analysis
for Spring Boot projects with multiple datasource support.

Usage:
    mcp-spring-db-tools <application_yml_path> <jasypt_key> [jasypt_algorithm] [jasypt_salt]

Arguments:
    application_yml_path: Absolute path to Spring Boot application.yml
    jasypt_key: JASYPT_KEY for decrypting encrypted database credentials (use empty string if not encrypted)
    jasypt_algorithm: Optional Jasypt encryption algorithm (default: PBEWithMD5AndDES)
    jasypt_salt: Optional fixed salt for StringFixedSaltGenerator (empty for RandomSaltGenerator)
"""

import sys
import logging
from typing import Any

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.types import Tool, TextContent

from .common.yaml_parser import ApplicationYamlParser, DataSourceConfig
from .common.properties_parser import ApplicationPropertiesParser
from .common.db_connector import create_connector, DatabaseConnector
from .tools.schema_tool import get_schema_info, format_schema_info
from .tools.execution_plan_tool import get_execution_plan, validate_query, format_execution_plan_result
from .tools.datasource_tool import list_datasources

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class SpringDBToolsServer:
    """
    MCP Server that provides database tools for Spring Boot projects.
    
    Tools:
        1. get_schema_info: Get database schema including tables, columns, and indexes
        2. get_execution_plan: Get query execution plan for performance analysis
        3. list_datasources: List all configured datasources
    """
    
    def __init__(
        self,
        yaml_path: str,
        jasypt_key: str = "",
        jasypt_algorithm: str = "PBEWithMD5AndDES",
        jasypt_salt: str = ""
    ):
        """
        Initialize the server with Spring Boot configuration.
        
        Args:
            yaml_path: Path to application.yml or application.properties file
            jasypt_key: JASYPT_KEY for decryption (empty string if not needed)
            jasypt_algorithm: Jasypt encryption algorithm (default: PBEWithMD5AndDES)
            jasypt_salt: Fixed salt for StringFixedSaltGenerator (empty if RandomSaltGenerator)
        """
        self.yaml_path = yaml_path
        self.jasypt_key = jasypt_key if jasypt_key else None
        self.jasypt_algorithm = jasypt_algorithm
        self.jasypt_salt = jasypt_salt if jasypt_salt else None
        self.datasources: list[DataSourceConfig] = []
        self.connectors: dict[str, DatabaseConnector] = {}
        self.server = Server("mcp-spring-db-tools")
        
        self._setup_handlers()
        
    def _setup_handlers(self):
        """Set up MCP request handlers."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """Return list of available tools."""
            tools = [
                Tool(
                    name="get_schema_info",
                    description=(
                        "Get database schema information including tables, columns, indexes, "
                        "and foreign keys. Use this to understand database structure for development. "
                        "Returns detailed schema info for the specified datasource."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "datasource_name": {
                                "type": "string",
                                "description": (
                                    "Name of the datasource to query. Use 'list' to see available datasources, "
                                    "or leave empty to use the first/default datasource."
                                )
                            },
                            "table_name": {
                                "type": "string",
                                "description": (
                                    "Optional: Specific table name to get schema for. "
                                    "Leave empty to get all tables."
                                )
                            }
                        },
                        "required": []
                    }
                ),
                Tool(
                    name="get_execution_plan",
                    description=(
                        "Analyze SQL query and return its execution plan. "
                        "Use this to understand query performance, identify missing indexes, "
                        "and optimize queries. Supports SELECT, INSERT, UPDATE, DELETE queries."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "datasource_name": {
                                "type": "string",
                                "description": (
                                    "Name of the datasource to execute the query against. "
                                    "Leave empty to use the first/default datasource."
                                )
                            },
                            "query": {
                                "type": "string",
                                "description": "SQL query to analyze (SELECT, INSERT, UPDATE, DELETE)"
                            }
                        },
                        "required": ["query"]
                    }
                ),
                Tool(
                    name="list_datasources",
                    description=(
                        "List all available datasources configured in the Spring Boot application configuration. "
                        "Shows datasource names, database types, and connection status."
                    ),
                    inputSchema={
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )
            ]
            return tools
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
            """Handle tool calls."""
            try:
                if name == "list_datasources":
                    result = self._handle_list_datasources()
                elif name == "get_schema_info":
                    datasource_name = (arguments or {}).get("datasource_name", "")
                    table_name = (arguments or {}).get("table_name", "")
                    result = self._handle_get_schema_info(datasource_name, table_name)
                elif name == "get_execution_plan":
                    datasource_name = (arguments or {}).get("datasource_name", "")
                    query = (arguments or {}).get("query", "")
                    if not query:
                        result = "Error: 'query' parameter is required"
                    else:
                        result = self._handle_get_execution_plan(datasource_name, query)
                else:
                    result = f"Error: Unknown tool '{name}'"
                
                return [TextContent(type="text", text=result)]
                
            except Exception as e:
                logger.exception(f"Error executing tool {name}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    def _parse_config(self):
        """Parse configuration file (yml or properties) and initialize datasources."""
        try:
            if self.yaml_path.endswith('.properties'):
                parser = ApplicationPropertiesParser(
                    self.yaml_path,
                    self.jasypt_key,
                    self.jasypt_algorithm,
                    self.jasypt_salt
                )
            else:
                parser = ApplicationYamlParser(
                    self.yaml_path,
                    self.jasypt_key,
                    self.jasypt_algorithm,
                    self.jasypt_salt
                )
                
            self.datasources = parser.parse()
            
            if not self.datasources:
                raise ValueError(f"No datasources found in {self.yaml_path}")
            
            logger.info(f"Found {len(self.datasources)} datasource(s)")
            for ds in self.datasources:
                logger.info(f"  - {ds.name}: {ds.db_type} ({ds.database})")
                
        except Exception as e:
            logger.error(f"Failed to parse configuration: {e}")
            raise
    
    def _get_connector(self, datasource_name: str = "") -> tuple[str, DatabaseConnector]:
        """
        Get or create a database connector for the specified datasource.
        
        Args:
            datasource_name: Name of the datasource (empty for default/first)
            
        Returns:
            Tuple of (datasource_name, connector)
        """
        if not self.datasources:
            self._parse_config()
        
        # Find the datasource
        if datasource_name:
            ds = next((d for d in self.datasources if d.name == datasource_name), None)
            if not ds:
                available = [d.name for d in self.datasources]
                raise ValueError(f"Datasource '{datasource_name}' not found. Available: {available}")
        else:
            ds = self.datasources[0]
        
        # Get or create connector
        if ds.name not in self.connectors:
            connector = create_connector(ds)
            self.connectors[ds.name] = connector
        
        return ds.name, self.connectors[ds.name]
    
    def _handle_list_datasources(self) -> str:
        """Handle list_datasources tool call."""
        if not self.datasources:
            self._parse_config()
        
        return list_datasources(self.datasources)
    
    def _handle_get_schema_info(self, datasource_name: str = "", table_name: str = "") -> str:
        """Handle get_schema_info tool call."""
        ds_name, connector = self._get_connector(datasource_name)
        
        try:
            schema_info = get_schema_info(connector, table_name)
            
            if table_name and not schema_info.get('tables'):
                return f"Table '{table_name}' not found in datasource '{ds_name}'"
            
            return format_schema_info(ds_name, schema_info)
            
        except Exception as e:
            return f"Error getting schema for datasource '{ds_name}': {str(e)}"
    
    def _handle_get_execution_plan(self, datasource_name: str = "", query: str = "") -> str:
        """Handle get_execution_plan tool call."""
        # Validate query first
        is_valid, error_message = validate_query(query)
        if not is_valid:
            return error_message
        
        ds_name, connector = self._get_connector(datasource_name)
        
        try:
            plan = get_execution_plan(connector, query)
            return format_execution_plan_result(ds_name, query, plan)
            
        except Exception as e:
            return f"Error getting execution plan for datasource '{ds_name}': {str(e)}"
    
    async def run(self):
        """Run the MCP server using stdio transport."""
        from mcp.server.stdio import stdio_server
        
        # Parse config on startup to validate
        try:
            self._parse_config()
        except Exception as e:
            logger.error(f"Failed to initialize: {e}")
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        
        logger.info("Starting MCP Spring DB Tools server (stdio mode)")
        
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="mcp-spring-db-tools",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )


def main():
    """Main entry point for the MCP server."""
    import asyncio
    
    # Parse command line arguments with backward compatibility
    if len(sys.argv) < 3:
        print(
            "Usage: mcp-spring-db-tools <application_yml_path> <jasypt_key> [jasypt_algorithm] [jasypt_salt]\n\n"
            "Arguments:\n"
            "  application_yml_path  Absolute path to Spring Boot application.yml\n"
            "  jasypt_key            JASYPT_KEY for decryption (use empty quotes \"\" if not encrypted)\n"
            "  jasypt_algorithm      Optional: Jasypt algorithm (default: PBEWithMD5AndDES)\n"
            "                        Supported: PBEWithMD5AndDES, PBEWithMD5AndTripleDES, PBEWITHHMACSHA512ANDAES_256\n"
            "  jasypt_salt           Optional: Fixed salt for StringFixedSaltGenerator\n"
            "                        (leave empty for RandomSaltGenerator)\n\n"
            "Examples:\n"
            "  # No encryption\n"
            '  mcp-spring-db-tools /path/to/application.yml ""\n\n'
            "  # Jasypt with RandomSaltGenerator (default)\n"
            '  mcp-spring-db-tools /path/to/application.yml "my-secret-key"\n\n'
            "  # Jasypt with custom algorithm and RandomSaltGenerator\n"
            '  mcp-spring-db-tools /path/to/application.yml "my-key" "PBEWithMD5AndTripleDES"\n\n'
            "  # Jasypt with FixedSaltGenerator\n"
            '  mcp-spring-db-tools /path/to/application.yml "my-key" "PBEWithMD5AndDES" "my-salt"\n',
            file=sys.stderr
        )
        sys.exit(1)
    
    yaml_path = sys.argv[1]
    jasypt_key = sys.argv[2]
    jasypt_algorithm = sys.argv[3] if len(sys.argv) > 3 else "PBEWithMD5AndDES"
    jasypt_salt = sys.argv[4] if len(sys.argv) > 4 else ""
    
    # Create and run server
    server = SpringDBToolsServer(yaml_path, jasypt_key, jasypt_algorithm, jasypt_salt)
    asyncio.run(server.run())


if __name__ == "__main__":
    main()
