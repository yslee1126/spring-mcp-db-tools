"""
Spring Boot application.yml parser module.
Extracts datasource configurations from Spring Boot configuration files.
"""

import os
import re
from pathlib import Path
from typing import Any
from dataclasses import dataclass

import yaml

from .jasypt_decryptor import JasyptDecryptor


@dataclass
class DataSourceConfig:
    """Represents a single datasource configuration."""
    name: str
    url: str
    username: str
    password: str
    driver_class: str
    db_type: str  # mysql, postgresql, h2, oracle, etc.
    base_path: str = None  # Project root for resolving relative paths (e.g., SQLite files)
    
    @property
    def host(self) -> str:
        """Extract host from JDBC URL."""
        return self._parse_jdbc_url().get('host', 'localhost')
    
    @property
    def port(self) -> int:
        """Extract port from JDBC URL."""
        return self._parse_jdbc_url().get('port', 3306)
    
    @property
    def database(self) -> str:
        """Extract database name from JDBC URL."""
        return self._parse_jdbc_url().get('database', '')
    
    def _parse_jdbc_url(self) -> dict:
        """Parse JDBC URL to extract connection details."""
        result = {'host': 'localhost', 'port': 3306, 'database': ''}
        
        # Handle different JDBC URL formats
        # MySQL: jdbc:mysql://host:port/database
        # PostgreSQL: jdbc:postgresql://host:port/database
        # H2: jdbc:h2:file:./path or jdbc:h2:mem:dbname or jdbc:h2:tcp://host:port/path
        # Oracle: jdbc:oracle:thin:@host:port:sid or jdbc:oracle:thin:@//host:port/service
        
        url = self.url
        
        # MySQL pattern
        mysql_match = re.match(r'jdbc:mysql://([^:/]+):?(\d+)?/([^?]+)', url)
        if mysql_match:
            result['host'] = mysql_match.group(1)
            result['port'] = int(mysql_match.group(2)) if mysql_match.group(2) else 3306
            result['database'] = mysql_match.group(3)
            return result
        
        # PostgreSQL pattern
        pg_match = re.match(r'jdbc:postgresql://([^:/]+):?(\d+)?/([^?]+)', url)
        if pg_match:
            result['host'] = pg_match.group(1)
            result['port'] = int(pg_match.group(2)) if pg_match.group(2) else 5432
            result['database'] = pg_match.group(3)
            return result
        
        # H2 file pattern
        h2_file_match = re.match(r'jdbc:h2:file:([^;]+)', url)
        if h2_file_match:
            result['host'] = 'file'
            result['port'] = 0
            result['database'] = h2_file_match.group(1)
            return result
        
        # H2 mem pattern
        h2_mem_match = re.match(r'jdbc:h2:mem:([^;]+)', url)
        if h2_mem_match:
            result['host'] = 'mem'
            result['port'] = 0
            result['database'] = h2_mem_match.group(1)
            return result
        
        # H2 TCP pattern
        h2_tcp_match = re.match(r'jdbc:h2:tcp://([^:/]+):?(\d+)?/([^;]+)', url)
        if h2_tcp_match:
            result['host'] = h2_tcp_match.group(1)
            result['port'] = int(h2_tcp_match.group(2)) if h2_tcp_match.group(2) else 9092
            result['database'] = h2_tcp_match.group(3)
            return result
        
        # Oracle thin pattern
        oracle_match = re.match(r'jdbc:oracle:thin:@//([^:/]+):?(\d+)?/([^?]+)', url)
        if oracle_match:
            result['host'] = oracle_match.group(1)
            result['port'] = int(oracle_match.group(2)) if oracle_match.group(2) else 1521
            result['database'] = oracle_match.group(3)
            return result
            
        # MSSQL pattern
        # jdbc:sqlserver://localhost:1433;databaseName=adventure
        mssql_match = re.match(r'jdbc:sqlserver://([^:;]+):?(\d+)?(?:;.*databaseName=([^;]+))?', url)
        if mssql_match:
            result['host'] = mssql_match.group(1)
            result['port'] = int(mssql_match.group(2)) if mssql_match.group(2) else 1433
            # databaseName might be in connection properties
            db_name = mssql_match.group(3)
            if not db_name:
                # Try finding databaseName parameter if not matched in the main group
                db_param = re.search(r'databaseName=([^;]+)', url)
                if db_param:
                    db_name = db_param.group(1)
            result['database'] = db_name if db_name else ''
            return result
        
        # SQLite pattern
        # jdbc:sqlite:/path/to/database.db or jdbc:sqlite:./relative/path.db
        sqlite_match = re.match(r'jdbc:sqlite:(.+)', url)
        if sqlite_match:
            result['host'] = 'file'
            result['port'] = 0
            result['database'] = sqlite_match.group(1)
            return result
        
        return result


class ApplicationYamlParser:
    """
    Parses Spring Boot application.yml files to extract datasource configurations.
    Supports multiple datasources and Jasypt encryption.
    """
    
    def __init__(
        self,
        yaml_path: str,
        jasypt_key: str = None,
        jasypt_algorithm: str = "PBEWithMD5AndDES",
        jasypt_salt: str = None,
        jasypt_iterations: int = 1000
    ):
        """
        Initialize the parser.
        
        Args:
            yaml_path: Absolute path to the application.yml file
            jasypt_key: Optional JASYPT_KEY for decrypting encrypted values
            jasypt_algorithm: Jasypt encryption algorithm (default: PBEWithMD5AndDES)
            jasypt_salt: Optional fixed salt for StringFixedSaltGenerator
            jasypt_iterations: Number of iterations for key derivation (default: 1000)
        """
        self.yaml_path = Path(yaml_path)
        self.jasypt_key = jasypt_key
        self.jasypt_algorithm = jasypt_algorithm
        self.jasypt_salt = jasypt_salt
        self.jasypt_iterations = jasypt_iterations
        self.decryptor = JasyptDecryptor(
            jasypt_key,
            algorithm=jasypt_algorithm,
            fixed_salt=jasypt_salt,
            iterations=jasypt_iterations
        ) if jasypt_key else None
        
        if not self.yaml_path.exists():
            raise FileNotFoundError(f"application.yml not found: {yaml_path}")
        
        # Calculate project root (assuming application.yml is in src/main/resources)
        # Go up 3 levels: resources -> main -> src -> project_root
        # If not in standard location, use the parent directory
        potential_root = self.yaml_path.parent.parent.parent.parent
        if potential_root.exists() and (potential_root / 'src').exists():
            self.project_root = potential_root
        else:
            # Fallback: use the directory containing application.yml's parent
            self.project_root = self.yaml_path.parent
    
    def _resolve_env_variables(self, value: str) -> str:
        """
        Resolve environment variable placeholders like ${VAR_NAME} or ${VAR_NAME:default}.
        
        Args:
            value: String potentially containing environment variable placeholders
            
        Returns:
            String with placeholders resolved
        """
        if not isinstance(value, str):
            return value
        
        # Pattern: ${VAR_NAME} or ${VAR_NAME:default_value}
        pattern = r'\$\{([^}:]+)(?::([^}]*))?\}'
        
        def replace_match(match):
            var_name = match.group(1)
            default_value = match.group(2) if match.group(2) is not None else ''
            return os.environ.get(var_name, default_value)
        
        return re.sub(pattern, replace_match, value)
    
    def _decrypt_value(self, value: str) -> str:
        """
        Decrypt a value if it's Jasypt-encrypted and a key is available.
        
        Args:
            value: The value to potentially decrypt
            
        Returns:
            Decrypted or original value
        """
        if not isinstance(value, str):
            return value
            
        # First resolve environment variables
        value = self._resolve_env_variables(value)
        
        # Then decrypt if needed
        if self.decryptor:
            return self.decryptor.decrypt_if_encrypted(value)
        return value
    
    def _detect_db_type(self, url: str, driver_class: str = None) -> str:
        """
        Detect the database type from URL or driver class.
        
        Args:
            url: JDBC URL
            driver_class: Optional driver class name
            
        Returns:
            Database type string (mysql, postgresql, h2, oracle, etc.)
        """
        url_lower = url.lower() if url else ''
        driver_lower = (driver_class or '').lower()
        
        if 'mysql' in url_lower or 'mysql' in driver_lower:
            return 'mysql'
        elif 'postgresql' in url_lower or 'postgres' in driver_lower:
            return 'postgresql'
        elif 'h2' in url_lower or 'h2' in driver_lower:
            return 'h2'
        elif 'sqlite' in url_lower or 'sqlite' in driver_lower:
            return 'sqlite'
        elif 'oracle' in url_lower or 'oracle' in driver_lower:
            return 'oracle'
        elif 'mariadb' in url_lower or 'mariadb' in driver_lower:
            return 'mariadb'
        elif 'sqlserver' in url_lower or 'sqlserver' in driver_lower:
            return 'sqlserver'
        else:
            return 'unknown'
    
    def _extract_single_datasource(self, ds_config: dict, name: str = 'default') -> DataSourceConfig:
        """
        Extract a single datasource configuration from a config dictionary.
        
        Args:
            ds_config: Dictionary containing datasource properties
            name: Name for this datasource
            
        Returns:
            DataSourceConfig object
        """
        url = self._decrypt_value(ds_config.get('url', ds_config.get('jdbc-url', '')))
        username = self._decrypt_value(ds_config.get('username', ''))
        password = self._decrypt_value(ds_config.get('password', ''))
        driver_class = ds_config.get('driver-class-name', ds_config.get('driverClassName', ''))
        
        db_type = self._detect_db_type(url, driver_class)
        
        return DataSourceConfig(
            name=name,
            url=url,
            username=username,
            password=password,
            driver_class=driver_class,
            db_type=db_type,
            base_path=str(self.project_root)
        )
    
    def parse(self) -> list[DataSourceConfig]:
        """
        Parse the application.yml file and extract all datasource configurations.
        
        Returns:
            List of DataSourceConfig objects
        """
        with open(self.yaml_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            return []
        
        datasources = []
        
        # Check for spring.datasource (single datasource)
        spring_config = config.get('spring', {})
        
        # Standard single datasource
        if 'datasource' in spring_config:
            ds = spring_config['datasource']
            
            # Check if it's a simple datasource or has nested datasources
            if 'url' in ds or 'jdbc-url' in ds:
                # Simple single datasource
                datasources.append(self._extract_single_datasource(ds, 'primary'))
            else:
                # Multiple datasources under spring.datasource
                for ds_name, ds_config in ds.items():
                    if isinstance(ds_config, dict) and ('url' in ds_config or 'jdbc-url' in ds_config):
                        datasources.append(self._extract_single_datasource(ds_config, ds_name))
        
        # Check for arbitrary keys under spring that might contain datasource
        # Example: spring.primary-db.datasource
        for key, value in spring_config.items():
            if key == 'datasource':
                continue
                
            if isinstance(value, dict) and 'datasource' in value:
                ds = value['datasource']
                if isinstance(ds, dict) and ('url' in ds or 'jdbc-url' in ds):
                    # Use the key as the datasource name (e.g., primary-db)
                    datasources.append(self._extract_single_datasource(ds, key))
        
        # Check for multiple datasources pattern (common in multi-datasource setups)
        # Pattern: spring.datasource.primary, spring.datasource.secondary
        # Or: datasources.primary, datasources.secondary
        
        if 'datasources' in config:
            for ds_name, ds_config in config['datasources'].items():
                if isinstance(ds_config, dict):
                    datasources.append(self._extract_single_datasource(ds_config, ds_name))
        
        # Another common pattern: spring.jpa.databases or app.datasources
        if 'app' in config and 'datasources' in config['app']:
            for ds_name, ds_config in config['app']['datasources'].items():
                if isinstance(ds_config, dict):
                    datasources.append(self._extract_single_datasource(ds_config, ds_name))
        
        return datasources
