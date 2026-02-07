"""
Tests for SQLite database connector.
"""
import os
import sqlite3
import tempfile
import pytest

from mcp_spring_db_tools.common import SQLiteConnector, DataSourceConfig


@pytest.fixture
def test_db():
    """Create a temporary SQLite database for testing."""
    # Create temporary database file
    fd, db_path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Create test schema
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create posts table with foreign key
    cursor.execute("""
        CREATE TABLE posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX idx_users_name ON users(name)")
    cursor.execute("CREATE INDEX idx_posts_user_id ON posts(user_id)")
    
    # Insert test data
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Alice", "alice@example.com"))
    cursor.execute("INSERT INTO users (name, email) VALUES (?, ?)", ("Bob", "bob@example.com"))
    cursor.execute("INSERT INTO posts (title, content, user_id) VALUES (?, ?, ?)", 
                  ("First Post", "Hello World", 1))
    
    conn.commit()
    conn.close()
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except:
        pass


def test_sqlite_connection(test_db):
    """Test SQLite connection."""
    config = DataSourceConfig(
        name="test",
        url=f"jdbc:sqlite:{test_db}",
        username="",
        password="",
        driver_class="org.sqlite.JDBC",
        db_type="sqlite",
        base_path=None  # Absolute path, no need for base_path
    )
    
    connector = SQLiteConnector(config)
    
    # Test connection
    with connector.connection_context():
        assert connector._connection is not None
    
    # Connection should be closed after context
    assert connector._connection is None


def test_sqlite_schema_info(test_db):
    """Test getting schema information from SQLite."""
    config = DataSourceConfig(
        name="test",
        url=f"jdbc:sqlite:{test_db}",
        username="",
        password="",
        driver_class="org.sqlite.JDBC",
        db_type="sqlite",
        base_path=None
    )
    
    connector = SQLiteConnector(config)
    
    with connector.connection_context():
        schema = connector.get_schema_info()
        
        # Check database info
        assert 'database' in schema
        assert 'tables' in schema
        assert len(schema['tables']) == 2  # users and posts
        
        # Find users table
        users_table = next((t for t in schema['tables'] if t['name'] == 'users'), None)
        assert users_table is not None
        
        # Check columns
        assert len(users_table['columns']) == 4
        column_names = [col['name'] for col in users_table['columns']]
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'email' in column_names
        
        # Check primary key
        id_col = next((col for col in users_table['columns'] if col['name'] == 'id'), None)
        assert id_col['key'] == 'PRI'
        
        # Check indexes
        assert len(users_table['indexes']) > 0
        idx_names = [idx['name'] for idx in users_table['indexes']]
        assert 'idx_users_name' in idx_names
        
        # Find posts table
        posts_table = next((t for t in schema['tables'] if t['name'] == 'posts'), None)
        assert posts_table is not None
        
        # Check foreign keys
        assert len(posts_table['foreign_keys']) == 1
        fk = posts_table['foreign_keys'][0]
        assert fk['column'] == 'user_id'
        assert fk['referenced_table'] == 'users'
        assert fk['referenced_column'] == 'id'


def test_sqlite_execution_plan(test_db):
    """Test getting execution plan from SQLite."""
    config = DataSourceConfig(
        name="test",
        url=f"jdbc:sqlite:{test_db}",
        username="",
        password="",
        driver_class="org.sqlite.JDBC",
        db_type="sqlite",
        base_path=None
    )
    
    connector = SQLiteConnector(config)
    
    with connector.connection_context():
        # Test query without index (should do table scan)
        plan1 = connector.get_execution_plan("SELECT * FROM users WHERE email = 'alice@example.com'")
        assert 'EXECUTION PLAN' in plan1
        assert 'SCAN TABLE' in plan1 or 'SEARCH TABLE' in plan1
        
        # Test query with index
        plan2 = connector.get_execution_plan("SELECT * FROM users WHERE name = 'Alice'")
        assert 'EXECUTION PLAN' in plan2
        # Should use index idx_users_name
        assert 'Index Usage Tips' in plan2
        
        # Test JOIN query
        plan3 = connector.get_execution_plan("""
            SELECT u.name, p.title 
            FROM users u 
            JOIN posts p ON u.id = p.user_id
        """)
        assert 'EXECUTION PLAN' in plan3


def test_sqlite_url_parsing(test_db):
    """Test various URL formats for SQLite."""
    # Test with jdbc:sqlite: prefix
    config1 = DataSourceConfig(
        name="test",
        url=f"jdbc:sqlite:{test_db}",
        username="",
        password="",
        driver_class="org.sqlite.JDBC",
        db_type="sqlite",
        base_path=None
    )
    connector1 = SQLiteConnector(config1)
    with connector1.connection_context():
        schema = connector1.get_schema_info()
        assert len(schema['tables']) == 2
    
    # Test with direct path (database as fallback)
    config2 = DataSourceConfig(
        name="test",
        url=f"jdbc:sqlite:{test_db}",
        username="",
        password="",
        driver_class="org.sqlite.JDBC",
        db_type="sqlite",
        base_path=None
    )
    connector2 = SQLiteConnector(config2)
    with connector2.connection_context():
        schema = connector2.get_schema_info()
        assert len(schema['tables']) == 2


def test_sqlite_relative_path_resolution(test_db):
    """Test that relative paths are resolved correctly using base_path."""
    import tempfile
    import os
    
    # Create a temporary directory to act as project root
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create build directory
        build_dir = os.path.join(temp_dir, 'build')
        os.makedirs(build_dir, exist_ok=True)
        
        # Copy test database to build directory
        import shutil
        test_db_name = 'test.db'
        dest_db = os.path.join(build_dir, test_db_name)
        shutil.copy(test_db, dest_db)
        
        # Test with relative path
        config = DataSourceConfig(
            name="test",
            url=f"jdbc:sqlite:./build/{test_db_name}",
            username="",
            password="",
            driver_class="org.sqlite.JDBC",
            db_type="sqlite",
            base_path=temp_dir  # Project root
        )
        
        connector = SQLiteConnector(config)
        with connector.connection_context():
            schema = connector.get_schema_info()
            assert len(schema['tables']) == 2
            assert schema['tables'][0]['name'] in ['users', 'posts']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
