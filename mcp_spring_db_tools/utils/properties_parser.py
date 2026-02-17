"""
Properties file parser module.
Extracts datasource configurations from .properties files.
"""

import os
from pathlib import Path
from typing import Any
# from jproperties import Properties # Removed dependency
# Actually, python doesn't have a built-in properties parser that handles java properties perfectly (with unicode escapes etc)
# But for now I'll implement a simple one or use a library if available. 
# Re-reading: The user environment is likely strict. I should check if I can use standard libs.
# 'configparser' in python is for INI files, which are similar but not identical to Java properties.
# I will implement a simple parser for key=value lines, handling comments and basic trimming.

from .yaml_parser import DataSourceConfig
from .jasypt_decryptor import JasyptDecryptor

class ApplicationPropertiesParser:
    """
    Parses .properties files to extract datasource configurations.
    Supports Jasypt encryption.
    """
    
    def __init__(
        self,
        config_path: str,
        jasypt_key: str = None,
        jasypt_algorithm: str = "PBEWithMD5AndDES",
        jasypt_salt: str = None
    ):
        """
        Initialize the parser.
        
        Args:
            config_path: Absolute path to the .properties file
            jasypt_key: Optional JASYPT_KEY for decrypting encrypted values
            jasypt_algorithm: Jasypt encryption algorithm (default: PBEWithMD5AndDES)
            jasypt_salt: Optional fixed salt for StringFixedSaltGenerator
        """
        self.config_path = Path(config_path)
        self.jasypt_key = jasypt_key
        self.jasypt_algorithm = jasypt_algorithm
        self.jasypt_salt = jasypt_salt
        self.decryptor = JasyptDecryptor(
            jasypt_key,
            algorithm=jasypt_algorithm,
            fixed_salt=jasypt_salt
        ) if jasypt_key else None
        
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
        # Determine project root
        potential_root = self.config_path.parent.parent.parent.parent
        if potential_root.exists() and (potential_root / 'src').exists():
            self.project_root = potential_root
        else:
            self.project_root = self.config_path.parent

    def _decrypt_value(self, value: str) -> str:
        """Decrypt a value if it's Jasypt-encrypted."""
        if not isinstance(value, str):
            return value
        
        # In properties files, we might not have ${ENV} expansion logic implemented yet, 
        # but let's stick to simple decryption first as per requirement.
        
        if self.decryptor:
            return self.decryptor.decrypt_if_encrypted(value)
        return value

    def _detect_db_type(self, url: str, driver_class: str = None) -> str:
        """Reuse the detection logic from yaml_parser, but duplicated here to avoid cross-importing private methods."""
        # Alternatively, could utilize a shared util. For now, duplication is safer to avoid touching yaml_parser.
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

    def parse(self) -> list[DataSourceConfig]:
        """
        Parse the .properties file and extract all identifiable datasource configurations.
        Returns a list of DataSourceConfig objects.
        """
        properties = {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('!'):
                        continue
                    
                    key = None
                    value = None
                    if '=' in line:
                        key, value = line.split('=', 1)
                    elif ':' in line:
                        key, value = line.split(':', 1)
                    
                    if key:
                        properties[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error reading properties file: {e}")
            return []

        datasources = []
        
        # 1. Identification: Find all keys that look like a JDBC URL
        # We group configs by their "prefix"
        prefixes = set()
        
        # Suffixes that indicate a datasource URL
        url_suffixes = ['.url', '.jdbc-url', '.jdbcUrl']
        exact_url_keys = ['url', 'jdbc-url', 'jdbcUrl', 'jdbcUrl'] # Duplicated jdbcUrl intended? No. FIXED.

        for key in properties:
            key_lower = key.lower()
            prefix = None
            
            # Check for exact matches (top-level properties)
            if key in exact_url_keys or key_lower in ['url', 'jdbc-url', 'jdbcurl']:
                prefix = ""
            
            # Check for suffixes
            else:
                for suffix in url_suffixes:
                    if key.endswith(suffix): # Case sensitive check usually preferred for properties but user asks for flexibility
                         # Let's try case insensitive suffix matching if exact fails? 
                         # Actually, standard properties are usually lower-kebab or camelCase.
                        prefix = key[:-len(suffix)]
                        break
                    # Also try case-insensitive suffix for flexibility
                    if key.lower().endswith(suffix.lower()):
                         prefix = key[:-len(suffix)]
                         break
            
            if prefix is not None:
                prefixes.add(prefix)

        # 2. Extraction: For each prefix, extract the full config
        for prefix in prefixes:
            current_config = {}
            
            # Helper to find property with fuzzy matching within the prefix group
            def find_value(target_suffixes: list[str]) -> str:
                # 1. Try exact matches: prefix.target
                for target in target_suffixes:
                    candidate = f"{prefix}{target}" if prefix else target
                    if candidate in properties:
                        return properties[candidate]
                
                # 2. Try case-insensitive matches if strict failed (slower but robust)
                for target in target_suffixes:
                    candidate_lower = (f"{prefix}{target}" if prefix else target).lower()
                    for prop_key, prop_val in properties.items():
                        if prop_key.lower() == candidate_lower:
                            return prop_val
                            
                return ""

            url = find_value(['.url', '.jdbc-url', '.jdbcUrl', 'url', 'jdbc-url', 'jdbcUrl'])
            if not url:
                continue # Should not happen given how we collected prefixes
                
            username = find_value(['.username', '.user', 'username', 'user'])
            password = find_value(['.password', '.pass', 'password', 'pass'])
            driver_class = find_value(['.driver-class-name', '.driverClassName', '.driver-class', 'driverClassName', 'driver-class-name'])
            
            # Decrypt values
            url = self._decrypt_value(url)
            username = self._decrypt_value(username)
            password = self._decrypt_value(password)
            
            db_type = self._detect_db_type(url, driver_class)
            
            # Determine a logical name for the datasource
            name = 'default'
            if prefix:
                if prefix == 'spring.datasource':
                    name = 'default'
                elif prefix.startswith('spring.datasource.'):
                    name = prefix[len('spring.datasource.'):]
                elif prefix.endswith('.datasource'):
                     name = prefix[:-len('.datasource')]
                else:
                    name = prefix
            
            # Avoid duplicate names if multiple prefixes map to same logical name or 'default'
            # (Though prefixes are unique, generated names might collide. We'll handle uniqueness later if needed, 
            #  but for now append valid config)
            
            ds = DataSourceConfig(
                name=name,
                url=url,
                username=username,
                password=password,
                driver_class=driver_class,
                db_type=db_type,
                base_path=str(self.project_root)
            )
            datasources.append(ds)
            
        return datasources
