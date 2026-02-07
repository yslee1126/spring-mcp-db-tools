"""
Tests for YAML parser module.
"""

import tempfile
import os
import pytest

from mcp_spring_db_tools.common.yaml_parser import ApplicationYamlParser, DataSourceConfig


class TestDataSourceConfig:
    """Tests for DataSourceConfig class."""
    
    def test_mysql_url_parsing(self):
        """Test MySQL JDBC URL parsing."""
        config = DataSourceConfig(
            name="test",
            url="jdbc:mysql://localhost:3306/testdb",
            username="user",
            password="pass",
            driver_class="com.mysql.cj.jdbc.Driver",
            db_type="mysql"
        )
        
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.database == "testdb"
    
    def test_postgresql_url_parsing(self):
        """Test PostgreSQL JDBC URL parsing."""
        config = DataSourceConfig(
            name="test",
            url="jdbc:postgresql://db.example.com:5432/mydb",
            username="user",
            password="pass",
            driver_class="org.postgresql.Driver",
            db_type="postgresql"
        )
        
        assert config.host == "db.example.com"
        assert config.port == 5432
        assert config.database == "mydb"
    
    def test_mysql_url_default_port(self):
        """Test MySQL URL parsing with default port."""
        config = DataSourceConfig(
            name="test",
            url="jdbc:mysql://localhost/testdb",
            username="user",
            password="pass",
            driver_class="",
            db_type="mysql"
        )
        
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.database == "testdb"
    
    def test_h2_file_url_parsing(self):
        """Test H2 file URL parsing."""
        config = DataSourceConfig(
            name="test",
            url="jdbc:h2:file:./build/testdb",
            username="sa",
            password="",
            driver_class="org.h2.Driver",
            db_type="h2"
        )
        
        assert config.host == "file"
        assert config.port == 0
        assert config.database == "./build/testdb"
    
    def test_h2_mem_url_parsing(self):
        """Test H2 memory URL parsing."""
        config = DataSourceConfig(
            name="test",
            url="jdbc:h2:mem:testdb",
            username="sa",
            password="",
            driver_class="org.h2.Driver",
            db_type="h2"
        )
        
        assert config.host == "mem"
        assert config.port == 0
        assert config.database == "testdb"


class TestApplicationYamlParser:
    """Tests for ApplicationYamlParser class."""
    
    def test_single_datasource_parsing(self):
        """Test parsing single datasource configuration."""
        yaml_content = """
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/mydb
    username: admin
    password: secret
    driver-class-name: com.mysql.cj.jdbc.Driver
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                parser = ApplicationYamlParser(f.name)
                datasources = parser.parse()
                
                assert len(datasources) == 1
                ds = datasources[0]
                assert ds.name == "primary"
                assert ds.db_type == "mysql"
                assert ds.host == "localhost"
                assert ds.port == 3306
                assert ds.database == "mydb"
                assert ds.username == "admin"
                assert ds.password == "secret"
            finally:
                os.unlink(f.name)
    
    def test_multi_datasource_parsing(self):
        """Test parsing multiple datasource configuration."""
        yaml_content = """
spring:
  datasource:
    primary:
      url: jdbc:mysql://localhost:3306/main_db
      username: admin
      password: admin123
    secondary:
      url: jdbc:postgresql://localhost:5432/logs_db
      username: postgres
      password: postgres
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                parser = ApplicationYamlParser(f.name)
                datasources = parser.parse()
                
                assert len(datasources) == 2
                
                ds_names = {ds.name for ds in datasources}
                assert ds_names == {"primary", "secondary"}
                
                primary = next(ds for ds in datasources if ds.name == "primary")
                assert primary.db_type == "mysql"
                
                secondary = next(ds for ds in datasources if ds.name == "secondary")
                assert secondary.db_type == "postgresql"
            finally:
                os.unlink(f.name)
    
    def test_env_variable_resolution(self):
        """Test environment variable resolution in configuration."""
        yaml_content = """
spring:
  datasource:
    url: ${DATABASE_URL:jdbc:mysql://localhost:3306/default}
    username: ${DB_USER:admin}
    password: ${DB_PASSWORD}
"""
        # Set environment variables
        os.environ['DB_PASSWORD'] = 'test_password'
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                parser = ApplicationYamlParser(f.name)
                datasources = parser.parse()
                
                assert len(datasources) == 1
                ds = datasources[0]
                
                # Should use default values
                assert ds.database == "default"
                assert ds.username == "admin"
                # Should use environment variable
                assert ds.password == "test_password"
            finally:
                os.unlink(f.name)
                del os.environ['DB_PASSWORD']
    
    def test_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            ApplicationYamlParser("/nonexistent/path/application.yml")
    
    def test_db_type_detection(self):
        """Test database type detection from URL."""
        yaml_content = """
spring:
  datasource:
    url: jdbc:mariadb://localhost:3306/mydb
    username: admin
    password: secret
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            try:
                parser = ApplicationYamlParser(f.name)
                datasources = parser.parse()
                
                assert len(datasources) == 1
                assert datasources[0].db_type == "mariadb"
            finally:
                os.unlink(f.name)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
