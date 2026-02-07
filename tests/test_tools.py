"""
Tests for tool modules.
"""

import pytest

from mcp_spring_db_tools.tools.datasource_tool import list_datasources, get_datasource_summary
from mcp_spring_db_tools.tools.execution_plan_tool import validate_query


class TestDatasourceTool:
    """Tests for datasource tool functions."""
    
    def test_list_datasources_formatting(self):
        """Test datasource listing format."""
        # Create mock datasource configs
        class MockDataSource:
            def __init__(self, name, db_type, database, host, port, url):
                self.name = name
                self.db_type = db_type
                self.database = database
                self.host = host
                self.port = port
                self.url = url
        
        datasources = [
            MockDataSource("primary", "mysql", "main_db", "localhost", 3306, "jdbc:mysql://localhost:3306/main_db"),
            MockDataSource("secondary", "postgresql", "logs_db", "localhost", 5432, "jdbc:postgresql://localhost:5432/logs_db"),
        ]
        
        result = list_datasources(datasources)
        
        assert "CONFIGURED DATASOURCES" in result
        assert "primary" in result
        assert "secondary" in result
        assert "mysql" in result
        assert "postgresql" in result
        assert "Total: 2 datasource(s)" in result
    
    def test_get_datasource_summary(self):
        """Test datasource summary generation."""
        class MockDataSource:
            def __init__(self, name, db_type, database, host, port):
                self.name = name
                self.db_type = db_type
                self.database = database
                self.host = host
                self.port = port
        
        datasources = [
            MockDataSource("primary", "mysql", "main_db", "localhost", 3306),
        ]
        
        summary = get_datasource_summary(datasources)
        
        assert summary['count'] == 1
        assert len(summary['datasources']) == 1
        assert summary['datasources'][0]['name'] == "primary"


class TestExecutionPlanTool:
    """Tests for execution plan tool functions."""
    
    def test_validate_select_query(self):
        """Test validation of SELECT query."""
        is_valid, error = validate_query("SELECT * FROM users")
        assert is_valid is True
        assert error == ""
    
    def test_validate_insert_query(self):
        """Test validation of INSERT query."""
        is_valid, error = validate_query("INSERT INTO users (name) VALUES ('test')")
        assert is_valid is True
        assert error == ""
    
    def test_validate_update_query(self):
        """Test validation of UPDATE query."""
        is_valid, error = validate_query("UPDATE users SET name = 'test' WHERE id = 1")
        assert is_valid is True
        assert error == ""
    
    def test_validate_delete_query(self):
        """Test validation of DELETE query."""
        is_valid, error = validate_query("DELETE FROM users WHERE id = 1")
        assert is_valid is True
        assert error == ""
    
    def test_validate_with_query(self):
        """Test validation of WITH (CTE) query."""
        is_valid, error = validate_query("WITH cte AS (SELECT * FROM users) SELECT * FROM cte")
        assert is_valid is True
        assert error == ""
    
    def test_reject_create_query(self):
        """Test rejection of CREATE query."""
        is_valid, error = validate_query("CREATE TABLE test (id INT)")
        assert is_valid is False
        assert "DDL statements" in error
    
    def test_reject_drop_query(self):
        """Test rejection of DROP query."""
        is_valid, error = validate_query("DROP TABLE users")
        assert is_valid is False
        assert "DDL statements" in error
    
    def test_reject_alter_query(self):
        """Test rejection of ALTER query."""
        is_valid, error = validate_query("ALTER TABLE users ADD COLUMN email VARCHAR(255)")
        assert is_valid is False
        assert "DDL statements" in error
    
    def test_reject_truncate_query(self):
        """Test rejection of TRUNCATE query."""
        is_valid, error = validate_query("TRUNCATE TABLE users")
        assert is_valid is False
        assert "DDL statements" in error
    
    def test_case_insensitive_validation(self):
        """Test case-insensitive query validation."""
        is_valid, error = validate_query("select * from users")
        assert is_valid is True
        
        is_valid, error = validate_query("SELECT * FROM users")
        assert is_valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
