"""
Entry point for running mcp_spring_db_tools as a module.

This allows the package to be run with:
    python -m mcp_spring_db_tools <args>
"""

from .server import main

if __name__ == "__main__":
    main()
