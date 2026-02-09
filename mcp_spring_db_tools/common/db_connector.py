"""
Database connector module.
Provides connections and query execution for various database types.
"""

from abc import ABC, abstractmethod
from typing import Any
from contextlib import contextmanager

from .yaml_parser import DataSourceConfig


class DatabaseConnector(ABC):
    """Abstract base class for database connectors."""
    
    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._connection = None
    
    @abstractmethod
    def connect(self):
        """Establish a database connection."""
        pass
    
    @abstractmethod
    def disconnect(self):
        """Close the database connection."""
        pass
    
    @abstractmethod
    def get_schema_info(self, table_name: str = "") -> dict:
        """
        Get database schema information including tables, columns, and indexes.
        
        Args:
            table_name: Optional specific table name to query (supports wildcards)
            
        Returns:
            Dictionary containing schema information
        """
        pass
    
    @abstractmethod
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """
        Get stored procedures information.
        
        Args:
            procedure_name: Optional specific procedure name to query
            
        Returns:
            Dictionary containing stored procedures information
        """
        pass

    @abstractmethod
    def get_views_info(self, view_name: str = "") -> dict:
        """
        Get views information.
        
        Args:
            view_name: Optional specific view name to query
            
        Returns:
            Dictionary containing views information
        """
        pass

    @abstractmethod
    def get_execution_plan(self, query: str) -> str:
        """
        Get the execution plan for a SQL query.
        
        Args:
            query: SQL query to analyze
            
        Returns:
            Execution plan as a formatted string
        """
        pass
    
    @contextmanager
    def connection_context(self):
        """Context manager for database connections."""
        try:
            self.connect()
            yield self
        finally:
            self.disconnect()


class MySQLConnector(DatabaseConnector):
    """MySQL/MariaDB database connector."""
    
    def connect(self):
        import pymysql
        self._connection = pymysql.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.username,
            password=self.config.password,
            database=self.config.database,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get MySQL schema information."""
        schema_info = {
            'database': self.config.database,
            'tables': []
        }
        
        with self._connection.cursor() as cursor:
            # Get tables
            query = """
                SELECT TABLE_NAME, TABLE_COMMENT, TABLE_ROWS, ENGINE
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
            """
            params = [self.config.database]
            
            if table_name:
                query += " AND TABLE_NAME LIKE %s"
                params.append(table_name if '%' in table_name else table_name)
                
            query += " ORDER BY TABLE_NAME"
            
            cursor.execute(query, tuple(params))
            tables = cursor.fetchall()
            
            for table in tables:
                table_info = {
                    'name': table['TABLE_NAME'],
                    'comment': table['TABLE_COMMENT'],
                    'estimated_rows': table['TABLE_ROWS'],
                    'engine': table['ENGINE'],
                    'columns': [],
                    'indexes': [],
                    'foreign_keys': []
                }
                
                # Get columns
                cursor.execute("""
                    SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, 
                           COLUMN_DEFAULT, COLUMN_KEY, EXTRA, COLUMN_COMMENT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (self.config.database, table['TABLE_NAME']))
                columns = cursor.fetchall()
                
                for col in columns:
                    table_info['columns'].append({
                        'name': col['COLUMN_NAME'],
                        'type': col['COLUMN_TYPE'],
                        'nullable': col['IS_NULLABLE'] == 'YES',
                        'default': col['COLUMN_DEFAULT'],
                        'key': col['COLUMN_KEY'],
                        'extra': col['EXTRA'],
                        'comment': col['COLUMN_COMMENT']
                    })
                
                # Get indexes
                cursor.execute("""
                    SELECT INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS,
                           INDEX_TYPE
                    FROM INFORMATION_SCHEMA.STATISTICS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    GROUP BY INDEX_NAME, NON_UNIQUE, INDEX_TYPE
                    ORDER BY INDEX_NAME
                """, (self.config.database, table['TABLE_NAME']))
                indexes = cursor.fetchall()
                
                for idx in indexes:
                    table_info['indexes'].append({
                        'name': idx['INDEX_NAME'],
                        'unique': idx['NON_UNIQUE'] == 0,
                        'columns': idx['COLUMNS'].split(','),
                        'type': idx['INDEX_TYPE']
                    })
                
                # Get foreign keys
                cursor.execute("""
                    SELECT CONSTRAINT_NAME, COLUMN_NAME, 
                           REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    AND REFERENCED_TABLE_NAME IS NOT NULL
                    ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION
                """, (self.config.database, table['TABLE_NAME']))
                fks = cursor.fetchall()
                
                for fk in fks:
                    table_info['foreign_keys'].append({
                        'name': fk['CONSTRAINT_NAME'],
                        'column': fk['COLUMN_NAME'],
                        'referenced_table': fk['REFERENCED_TABLE_NAME'],
                        'referenced_column': fk['REFERENCED_COLUMN_NAME']
                    })
                
                schema_info['tables'].append(table_info)
        
        return schema_info
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get MySQL stored procedures."""
        procedures = []
        with self._connection.cursor() as cursor:
            # ROUTINE_DEFINITION might be null if user doesn't have privileges
            query = """
                SELECT ROUTINE_NAME, ROUTINE_DEFINITION, ROUTINE_COMMENT
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'
            """
            params = [self.config.database]
            
            if procedure_name:
                query += " AND ROUTINE_NAME LIKE %s"
                params.append(procedure_name if '%' in procedure_name else procedure_name)
                
            query += " ORDER BY ROUTINE_NAME"
            
            cursor.execute(query, tuple(params))
            
            for row in cursor.fetchall():
                procedures.append({
                    'name': row['ROUTINE_NAME'],
                    'definition': row['ROUTINE_DEFINITION'],
                    'comment': row['ROUTINE_COMMENT']
                })
        
        return {'database': self.config.database, 'procedures': procedures}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get MySQL views."""
        views = []
        with self._connection.cursor() as cursor:
            query = """
                SELECT TABLE_NAME, VIEW_DEFINITION
                FROM INFORMATION_SCHEMA.VIEWS
                WHERE TABLE_SCHEMA = %s
            """
            params = [self.config.database]
            
            if view_name:
                query += " AND TABLE_NAME LIKE %s"
                params.append(view_name if '%' in view_name else view_name)
                
            query += " ORDER BY TABLE_NAME"
            
            cursor.execute(query, tuple(params))
            
            for row in cursor.fetchall():
                views.append({
                    'name': row['TABLE_NAME'],
                    'definition': row['VIEW_DEFINITION']
                })
        
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get MySQL execution plan using EXPLAIN."""
        with self._connection.cursor() as cursor:
            # Use EXPLAIN ANALYZE for detailed execution plan (MySQL 8.0.18+)
            try:
                cursor.execute(f"EXPLAIN ANALYZE {query}")
                result = cursor.fetchall()
                return self._format_explain_result(result, 'analyze')
            except Exception:
                # Fall back to regular EXPLAIN
                cursor.execute(f"EXPLAIN {query}")
                result = cursor.fetchall()
                return self._format_explain_result(result, 'basic')
    
    def _format_explain_result(self, result: list, mode: str) -> str:
        """Format EXPLAIN result for display."""
        if mode == 'analyze':
            return '\n'.join([str(row) for row in result])
        
        lines = []
        lines.append("=" * 80)
        lines.append("EXECUTION PLAN")
        lines.append("=" * 80)
        
        for row in result:
            lines.append(f"\nTable: {row.get('table', 'N/A')}")
            lines.append(f"  Type: {row.get('type', 'N/A')}")
            lines.append(f"  Possible Keys: {row.get('possible_keys', 'N/A')}")
            lines.append(f"  Key: {row.get('key', 'N/A')}")
            lines.append(f"  Key Length: {row.get('key_len', 'N/A')}")
            lines.append(f"  Rows: {row.get('rows', 'N/A')}")
            lines.append(f"  Filtered: {row.get('filtered', 'N/A')}%")
            lines.append(f"  Extra: {row.get('Extra', 'N/A')}")
        
        return '\n'.join(lines)


class PostgreSQLConnector(DatabaseConnector):
    """PostgreSQL database connector."""
    
    def connect(self):
        import psycopg2
        import psycopg2.extras
        self._connection = psycopg2.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.username,
            password=self.config.password,
            dbname=self.config.database
        )
        self._connection.autocommit = True
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get PostgreSQL schema information."""
        import psycopg2.extras
        
        schema_info = {
            'database': self.config.database,
            'tables': []
        }
        
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get tables
            query = """
                SELECT t.table_name, 
                       obj_description((quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass) as table_comment,
                       (SELECT reltuples::bigint FROM pg_class WHERE oid = (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass) as estimated_rows
                FROM information_schema.tables t
                WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
            """
            params = []
            
            if table_name:
                query += " AND t.table_name LIKE %s"
                params.append(table_name if '%' in table_name else table_name)
                
            query += " ORDER BY t.table_name"
            
            cursor.execute(query, tuple(params))
            tables = cursor.fetchall()
            
            for table in tables:
                table_info = {
                    'name': table['table_name'],
                    'comment': table['table_comment'],
                    'estimated_rows': table['estimated_rows'],
                    'columns': [],
                    'indexes': [],
                    'foreign_keys': []
                }
                
                # Get columns
                cursor.execute("""
                    SELECT c.column_name, c.data_type, c.udt_name, c.is_nullable,
                           c.column_default,
                           col_description((quote_ident(c.table_schema) || '.' || quote_ident(c.table_name))::regclass, c.ordinal_position) as column_comment,
                           CASE WHEN pk.column_name IS NOT NULL THEN 'PRI' ELSE '' END as column_key
                    FROM information_schema.columns c
                    LEFT JOIN (
                        SELECT ku.column_name
                        FROM information_schema.table_constraints tc
                        JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
                        WHERE tc.table_name = %s AND tc.constraint_type = 'PRIMARY KEY'
                    ) pk ON c.column_name = pk.column_name
                    WHERE c.table_schema = 'public' AND c.table_name = %s
                    ORDER BY c.ordinal_position
                """, (table['table_name'], table['table_name']))
                columns = cursor.fetchall()
                
                for col in columns:
                    table_info['columns'].append({
                        'name': col['column_name'],
                        'type': col['udt_name'],
                        'nullable': col['is_nullable'] == 'YES',
                        'default': col['column_default'],
                        'key': col['column_key'],
                        'comment': col['column_comment']
                    })
                
                # Get indexes
                cursor.execute("""
                    SELECT i.relname as index_name,
                           ix.indisunique as is_unique,
                           array_agg(a.attname ORDER BY array_position(ix.indkey, a.attnum)) as columns,
                           am.amname as index_type
                    FROM pg_class t
                    JOIN pg_index ix ON t.oid = ix.indrelid
                    JOIN pg_class i ON i.oid = ix.indexrelid
                    JOIN pg_am am ON i.relam = am.oid
                    JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY(ix.indkey)
                    WHERE t.relname = %s AND t.relkind = 'r'
                    GROUP BY i.relname, ix.indisunique, am.amname
                    ORDER BY i.relname
                """, (table['table_name'],))
                indexes = cursor.fetchall()
                
                for idx in indexes:
                    table_info['indexes'].append({
                        'name': idx['index_name'],
                        'unique': idx['is_unique'],
                        'columns': idx['columns'],
                        'type': idx['index_type']
                    })
                
                # Get foreign keys
                cursor.execute("""
                    SELECT tc.constraint_name, kcu.column_name,
                           ccu.table_name as referenced_table,
                           ccu.column_name as referenced_column
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu 
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage ccu 
                        ON ccu.constraint_name = tc.constraint_name
                    WHERE tc.table_name = %s AND tc.constraint_type = 'FOREIGN KEY'
                """, (table['table_name'],))
                fks = cursor.fetchall()
                
                for fk in fks:
                    table_info['foreign_keys'].append({
                        'name': fk['constraint_name'],
                        'column': fk['column_name'],
                        'referenced_table': fk['referenced_table'],
                        'referenced_column': fk['referenced_column']
                    })
                
                schema_info['tables'].append(table_info)
        
        return schema_info
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get PostgreSQL stored procedures."""
        import psycopg2.extras
        
        procedures = []
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            # Get functions/procedures from public schema
            query = """
                SELECT n.nspname as schema, p.proname as name, 
                       pg_get_functiondef(p.oid) as definition,
                       d.description as comment
                FROM pg_proc p
                JOIN pg_namespace n ON p.pronamespace = n.oid
                LEFT JOIN pg_description d ON p.oid = d.objoid
                WHERE n.nspname = 'public'
            """
            params = []
            
            if procedure_name:
                query += " AND p.proname LIKE %s"
                params.append(procedure_name if '%' in procedure_name else procedure_name)
                
            query += " ORDER BY p.proname"
            
            cursor.execute(query, tuple(params))
            
            for row in cursor.fetchall():
                procedures.append({
                    'name': row['name'],
                    'definition': row['definition'],
                    'comment': row['comment']
                })
        
        return {'database': self.config.database, 'procedures': procedures}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get PostgreSQL views."""
        import psycopg2.extras
        
        views = []
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            query = """
                SELECT table_name, view_definition
                FROM information_schema.views
                WHERE table_schema = 'public'
            """
            params = []
            
            if view_name:
                query += " AND table_name LIKE %s"
                params.append(view_name if '%' in view_name else view_name)
                
            query += " ORDER BY table_name"
            
            cursor.execute(query, tuple(params))
            
            for row in cursor.fetchall():
                views.append({
                    'name': row['table_name'],
                    'definition': row['view_definition']
                })
        
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get PostgreSQL execution plan using EXPLAIN ANALYZE."""
        import psycopg2.extras
        
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            cursor.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query}")
            result = cursor.fetchall()
            
            lines = ["=" * 80, "EXECUTION PLAN", "=" * 80, ""]
            for row in result:
                lines.append(row[0])
            
            return '\n'.join(lines)


class MSSQLConnector(DatabaseConnector):
    """Microsoft SQL Server connector."""
    
    def connect(self):
        import pymssql
        self._connection = pymssql.connect(
            server=self.config.host,
            user=self.config.username,
            password=self.config.password,
            database=self.config.database,
            port=self.config.port or 1433,
            as_dict=True
        )
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
            
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get MSSQL schema information using INFORMATION_SCHEMA."""
        schema_info = {
            'database': self.config.database,
            'tables': []
        }
        
        with self._connection.cursor() as cursor:
            # Get tables using INFORMATION_SCHEMA
            query = """
                SELECT 
                    TABLE_SCHEMA,
                    TABLE_NAME,
                    TABLE_TYPE
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_TYPE = 'BASE TABLE'
            """
            params = []
            
            if table_name:
                query += " AND TABLE_NAME LIKE %s"
                params.append(table_name if '%' in table_name else table_name)
                
            query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
            
            cursor.execute(query, tuple(params))
            tables = cursor.fetchall()
            
            for table in tables:
                schema_name = table['TABLE_SCHEMA']
                table_name = table['TABLE_NAME']
                
                table_info = {
                    'name': table_name,  # Keep just table name for backward compatibility
                    'schema': schema_name,
                    'comment': None,
                    'estimated_rows': None,
                    'columns': [],
                    'indexes': [],
                    'foreign_keys': []
                }
                
                # Get columns using INFORMATION_SCHEMA
                cursor.execute("""
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        CHARACTER_MAXIMUM_LENGTH,
                        NUMERIC_PRECISION,
                        NUMERIC_SCALE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
                    ORDER BY ORDINAL_POSITION
                """, (schema_name, table_name))
                columns = cursor.fetchall()
                
                for col in columns:
                    col_name = col['COLUMN_NAME']
                    data_type = col['DATA_TYPE']
                    
                    # Add type details
                    if col['CHARACTER_MAXIMUM_LENGTH']:
                        if col['CHARACTER_MAXIMUM_LENGTH'] == -1:
                            data_type += "(MAX)"
                        else:
                            data_type += f"({col['CHARACTER_MAXIMUM_LENGTH']})"
                    elif col['NUMERIC_PRECISION']:
                        if col['NUMERIC_SCALE']:
                            data_type += f"({col['NUMERIC_PRECISION']},{col['NUMERIC_SCALE']})"
                        else:
                            data_type += f"({col['NUMERIC_PRECISION']})"
                    
                    table_info['columns'].append({
                        'name': col_name,
                        'type': data_type,
                        'nullable': col['IS_NULLABLE'] == 'YES',
                        'default': col['COLUMN_DEFAULT'],
                        'comment': None
                    })
                
                # Get primary keys using INFORMATION_SCHEMA
                try:
                    cursor.execute("""
                        SELECT 
                            kcu.COLUMN_NAME,
                            tc.CONSTRAINT_NAME
                        FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu
                            ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                            AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA
                            AND tc.TABLE_NAME = kcu.TABLE_NAME
                        WHERE tc.TABLE_SCHEMA = %s 
                            AND tc.TABLE_NAME = %s
                            AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                        ORDER BY kcu.ORDINAL_POSITION
                    """, (schema_name, table_name))
                    pk_columns = cursor.fetchall()
                    
                    if pk_columns:
                        pk_cols = [row['COLUMN_NAME'] for row in pk_columns]
                        pk_name = pk_columns[0]['CONSTRAINT_NAME']
                        table_info['indexes'].append({
                            'name': pk_name,
                            'unique': True,
                            'columns': pk_cols,
                            'type': 'PRIMARY KEY'
                        })
                except Exception:
                    # Skip if permission denied
                    pass
                
                # Get foreign keys using sys views (fallback to INFORMATION_SCHEMA if fails)
                try:
                    cursor.execute("""
                        SELECT 
                            fk.name AS FK_NAME,
                            COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS COLUMN_NAME,
                            OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS REF_SCHEMA,
                            OBJECT_NAME(fk.referenced_object_id) AS REF_TABLE,
                            COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS REF_COLUMN
                        FROM sys.foreign_keys fk
                        JOIN sys.foreign_key_columns fkc 
                            ON fk.object_id = fkc.constraint_object_id
                        WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id) = %s
                            AND OBJECT_NAME(fk.parent_object_id) = %s
                        ORDER BY fk.name, fkc.constraint_column_id
                    """, (schema_name, table_name))
                    fk_rows = cursor.fetchall()
                    
                    for row in fk_rows:
                        table_info['foreign_keys'].append({
                            'name': row['FK_NAME'],
                            'column': row['COLUMN_NAME'],
                            'referenced_table': f"{row['REF_SCHEMA']}.{row['REF_TABLE']}",
                            'referenced_column': row['REF_COLUMN']
                        })
                except Exception:
                    # Skip if permission denied
                    pass
                
                # Get indexes using sys views
                try:
                    cursor.execute("""
                        SELECT 
                            i.name AS INDEX_NAME,
                            i.type_desc AS INDEX_TYPE,
                            i.is_unique,
                            COL_NAME(ic.object_id, ic.column_id) AS COLUMN_NAME,
                            ic.is_descending_key
                        FROM sys.indexes i
                        JOIN sys.index_columns ic 
                            ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                        WHERE OBJECT_SCHEMA_NAME(i.object_id) = %s
                            AND OBJECT_NAME(i.object_id) = %s
                            AND i.type > 0
                            AND i.is_primary_key = 0
                        ORDER BY i.name, ic.key_ordinal
                    """, (schema_name, table_name))
                    index_rows = cursor.fetchall()
                    
                    # Group indexes
                    idx_map = {}
                    for row in index_rows:
                        idx_name = row['INDEX_NAME']
                        if idx_name not in idx_map:
                            idx_map[idx_name] = {
                                'name': idx_name,
                                'unique': row['is_unique'],
                                'type': row['INDEX_TYPE'],
                                'columns': []
                            }
                        col_order = f"{row['COLUMN_NAME']} DESC" if row['is_descending_key'] else row['COLUMN_NAME']
                        idx_map[idx_name]['columns'].append(col_order)
                    
                    table_info['indexes'].extend(list(idx_map.values()))
                except Exception:
                    # Skip if permission denied
                    pass
                
                schema_info['tables'].append(table_info)
        
        return schema_info


    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get MSSQL stored procedures."""
        procedures = []
        with self._connection.cursor() as cursor:
            query = """
                SELECT ROUTINE_SCHEMA, ROUTINE_NAME, ROUTINE_DEFINITION
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_TYPE = 'PROCEDURE'
            """
            params = []
            
            if procedure_name:
                query += " AND ROUTINE_NAME LIKE %s"
                params.append(procedure_name if '%' in procedure_name else procedure_name)
                
            query += " ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME"
            
            cursor.execute(query, tuple(params))
            
            for row in cursor.fetchall():
                procedures.append({
                    'schema': row['ROUTINE_SCHEMA'],
                    'name': row['ROUTINE_NAME'],
                    'definition': row['ROUTINE_DEFINITION']
                })
        
        return {'database': self.config.database, 'procedures': procedures}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get MSSQL views."""
        views = []
        with self._connection.cursor() as cursor:
            query = """
                SELECT TABLE_SCHEMA, TABLE_NAME, VIEW_DEFINITION
                FROM INFORMATION_SCHEMA.VIEWS
            """
            params = []
            
            if view_name:
                query += " WHERE TABLE_NAME LIKE %s"
                params.append(view_name if '%' in view_name else view_name)
                
            query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
            
            cursor.execute(query, tuple(params))
            
            for row in cursor.fetchall():
                views.append({
                    'schema': row['TABLE_SCHEMA'],
                    'name': row['TABLE_NAME'],
                    'definition': row['VIEW_DEFINITION']
                })
        
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get MSSQL execution plan."""
        with self._connection.cursor() as cursor:
            try:
                # Enable showplan
                cursor.execute("SET SHOWPLAN_TEXT ON")
                
                # Execute query (it won't actually run, just show plan)
                cursor.execute(query)
                result = cursor.fetchall()
                
                # Disable showplan
                cursor.execute("SET SHOWPLAN_TEXT OFF")
                
                lines = ["=" * 80, "EXECUTION PLAN", "=" * 80, ""]
                for row in result:
                    # SHOWPLAN_TEXT returns StmtText
                    lines.append(row['StmtText'])
                
                return '\n'.join(lines)
            except Exception as e:
                # Ensure showplan is off in case of error
                try:
                    cursor.execute("SET SHOWPLAN_TEXT OFF")
                except:
                    pass
                
                # Handle permission denied specifically (Error 262)
                error_str = str(e)
                if "SHOWPLAN permission denied" in error_str or "262" in error_str:
                    return (
                        "=" * 80 + "\n"
                        "⚠️ 실행 계획 권한 부족 (Permission Denied)\n"
                        "=" * 80 + "\n\n"
                        "현재 데이터베이스 사용자에게 'SHOWPLAN' 권한이 없어 실행 계획을 직접 추출할 수 없습니다.\n\n"
                        "💡 대안 및 권장 사항:\n"
                        "1. 테이블 스키마 조회 (`get_schema_info`)를 통해 인덱스 정보를 확인하세요.\n"
                        "   - WHERE 조건절에 사용된 컬럼에 인덱스가 있는지 확인\n"
                        "   - JOIN 조건 컬럼에 인덱스가 있는지 확인\n"
                        "   - ORDER BY 컬럼이 인덱스에 포함되는지 확인\n\n"
                        "2. 쿼리 최적화 팁:\n"
                        "   - SELECT * 사용 자제\n"
                        "   - LIKE '%keyword%' (Leading wildcard) 사용 시 인덱스 미사용 주의\n"
                        "   - 함수(컬럼) = 값 형태 대신 컬럼 = 값(함수) 형태 사용\n"
                    )
                
                raise e


class H2Connector(DatabaseConnector):
    """H2 database connector (TCP mode only for external connections)."""
    
    def connect(self):
        """
        Connect to H2 database.
        Note: H2 in embedded mode cannot be accessed by multiple processes.
        This connector works with H2 TCP server mode.
        """
        # For H2, we need to use jaydebeapi or a similar JDBC bridge
        # Since H2 is typically used for testing and development,
        # we provide a warning about limitations
        import pymysql
        
        if self.config.host in ('file', 'mem'):
            raise ConnectionError(
                "H2 embedded mode (file: or mem:) cannot be accessed externally. "
                "Please configure H2 with TCP server mode for MCP access, or use the "
                "Spring Boot application's H2 console for direct access."
            )
        
        # Try connecting via TCP mode
        # H2 with MySQL compatibility mode
        try:
            # Use JayDeBeApi for H2 JDBC connection
            import jaydebeapi
            
            self._connection = jaydebeapi.connect(
                'org.h2.Driver',
                self.config.url,
                [self.config.username, self.config.password],
                self.config.driver_path or '/path/to/h2.jar'
            )
        except ImportError:
            raise ConnectionError(
                "H2 database requires jaydebeapi library and H2 JDBC driver. "
                "Install with: pip install jaydebeapi\n"
                "And provide H2 JDBC driver jar path."
            )
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get H2 schema information."""
        # H2 uses standard SQL INFORMATION_SCHEMA
        schema_info = {
            'database': self.config.database,
            'tables': []
        }
        
        cursor = self._connection.cursor()
        try:
            # Get tables
            query = """
                SELECT TABLE_NAME, REMARKS
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_TYPE = 'TABLE'
            """
            params = []
            
            if table_name:
                query += " AND TABLE_NAME LIKE ?"
                params.append(table_name if '%' in table_name else table_name)
                
            query += " ORDER BY TABLE_NAME"
            
            cursor.execute(query, tuple(params))
            tables = cursor.fetchall()
            
            for table in tables:
                table_info = {
                    'name': table[0],
                    'comment': table[1],
                    'columns': [],
                    'indexes': []
                }
                
                # Get columns
                cursor.execute("""
                    SELECT COLUMN_NAME, TYPE_NAME, IS_NULLABLE, COLUMN_DEFAULT, REMARKS
                    FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = ?
                    ORDER BY ORDINAL_POSITION
                """, (table[0],))
                columns = cursor.fetchall()
                
                for col in columns:
                    table_info['columns'].append({
                        'name': col[0],
                        'type': col[1],
                        'nullable': col[2] == 'YES',
                        'default': col[3],
                        'comment': col[4]
                    })
                
                # Get indexes
                cursor.execute("""
                    SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME
                    FROM INFORMATION_SCHEMA.INDEXES
                    WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = ?
                    ORDER BY INDEX_NAME, ORDINAL_POSITION
                """, (table[0],))
                indexes_raw = cursor.fetchall()
                
                # Group by index name
                idx_map = {}
                for idx in indexes_raw:
                    if idx[0] not in idx_map:
                        idx_map[idx[0]] = {
                            'name': idx[0],
                            'unique': idx[1] == 0,
                            'columns': []
                        }
                    idx_map[idx[0]]['columns'].append(idx[2])
                
                table_info['indexes'] = list(idx_map.values())
                schema_info['tables'].append(table_info)
        finally:
            cursor.close()
        
        return schema_info
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get H2 stored procedures (Function Aliases)."""
        procedures = []
        cursor = self._connection.cursor()
        try:
            # H2 uses function aliases for stored procedures
            query = """
                SELECT ALIAS_NAME, JAVA_CLASS, METHOD_NAME 
                FROM INFORMATION_SCHEMA.FUNCTION_ALIASES
                WHERE ALIAS_SCHEMA = 'PUBLIC'
            """
            params = []
            
            if procedure_name:
                query += " AND ALIAS_NAME LIKE ?"
                params.append(procedure_name if '%' in procedure_name else procedure_name)
                
            query += " ORDER BY ALIAS_NAME"
            
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                procedures.append({
                    'name': row[0],
                    'definition': f"Java Class: {row[1]}, Method: {row[2]}"
                })
        except Exception:
            # Table might not exist in older versions
            pass
        finally:
            cursor.close()
        
        return {'database': self.config.database, 'procedures': procedures}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get H2 views."""
        views = []
        cursor = self._connection.cursor()
        try:
            query = """
                SELECT TABLE_NAME, VIEW_DEFINITION 
                FROM INFORMATION_SCHEMA.VIEWS 
                WHERE TABLE_SCHEMA = 'PUBLIC'
            """
            params = []
            
            if view_name:
                query += " AND TABLE_NAME LIKE ?"
                params.append(view_name if '%' in view_name else view_name)
                
            query += " ORDER BY TABLE_NAME"
            
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                views.append({
                    'name': row[0],
                    'definition': row[1]
                })
        finally:
            cursor.close()
        
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get H2 execution plan using EXPLAIN."""
        cursor = self._connection.cursor()
        try:
            cursor.execute(f"EXPLAIN {query}")
            result = cursor.fetchall()
            
            lines = ["=" * 80, "EXECUTION PLAN", "=" * 80, ""]
            for row in result:
                lines.append(str(row[0]))
            
            return '\n'.join(lines)
        finally:
            cursor.close()


class SQLiteConnector(DatabaseConnector):
    """SQLite database connector (using Python's built-in sqlite3)."""
    
    def connect(self):
        """
        Connect to SQLite database.
        SQLite files are accessed directly without network connection.
        """
        import sqlite3
        import os
        from pathlib import Path
        
        # Extract database path from URL
        # Format: jdbc:sqlite:/path/to/db.db or jdbc:sqlite:./relative/path.db
        db_path = self.config.database
        if self.config.url and 'jdbc:sqlite:' in self.config.url:
            db_path = self.config.url.replace('jdbc:sqlite:', '')
        
        # Resolve relative paths using base_path (project root)
        if db_path and not os.path.isabs(db_path):
            # Relative path - resolve using base_path
            if self.config.base_path:
                db_path = os.path.join(self.config.base_path, db_path)
            else:
                # Fallback to current working directory
                db_path = os.path.abspath(db_path)
        
        # Expand user home directory if present
        db_path = os.path.expanduser(db_path)
        
        # Check if database file exists (create parent directories if needed for new databases)
        db_path_obj = Path(db_path)
        if not db_path_obj.exists():
            # Create parent directories if they don't exist
            db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row  # Enable column access by name
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get SQLite schema information."""
        schema_info = {
            'database': self.config.database,
            'tables': []
        }
        
        cursor = self._connection.cursor()
        
        # Get tables (excluding internal sqlite tables)
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        params = []
        
        if table_name:
            query += " AND name LIKE ?"
            params.append(table_name if '%' in table_name else table_name)
            
        query += " ORDER BY name"
        
        cursor.execute(query, tuple(params))
        tables = cursor.fetchall()
        
        for table_row in tables:
            table_name = table_row['name']
            table_info = {
                'name': table_name,
                'comment': None,  # SQLite doesn't support table comments
                'columns': [],
                'indexes': [],
                'foreign_keys': []
            }
            
            # Get columns using PRAGMA
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            for col in columns:
                table_info['columns'].append({
                    'name': col['name'],
                    'type': col['type'],
                    'nullable': not col['notnull'],
                    'default': col['dflt_value'],
                    'key': 'PRI' if col['pk'] else '',
                    'comment': None  # SQLite doesn't support column comments
                })
            
            # Get indexes
            cursor.execute(f"PRAGMA index_list({table_name})")
            indexes = cursor.fetchall()
            
            for idx in indexes:
                # Get index columns
                cursor.execute(f"PRAGMA index_info({idx['name']})")
                idx_cols = cursor.fetchall()
                
                table_info['indexes'].append({
                    'name': idx['name'],
                    'unique': bool(idx['unique']),
                    'columns': [col['name'] for col in idx_cols],
                    'type': 'BTREE'  # SQLite primarily uses B-tree
                })
            
            # Get foreign keys
            cursor.execute(f"PRAGMA foreign_key_list({table_name})")
            fks = cursor.fetchall()
            
            for fk in fks:
                table_info['foreign_keys'].append({
                    'name': f"fk_{table_name}_{fk['id']}",
                    'column': fk['from'],
                    'referenced_table': fk['table'],
                    'referenced_column': fk['to']
                })
            
            schema_info['tables'].append(table_info)
        
        cursor.close()
        return schema_info
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get SQLite stored procedures (Not Supported)."""
        # SQLite does not support stored procedures
        return {'database': self.config.database, 'procedures': []}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get SQLite views."""
        views = []
        cursor = self._connection.cursor()
        try:
            query = "SELECT name, sql FROM sqlite_master WHERE type='view'"
            params = []
            
            if view_name:
                query += " AND name LIKE ?"
                params.append(view_name if '%' in view_name else view_name)
                
            query += " ORDER BY name"
            
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                views.append({
                    'name': row['name'],
                    'definition': row['sql']
                })
        finally:
            cursor.close()
        
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get SQLite execution plan using EXPLAIN QUERY PLAN."""
        cursor = self._connection.cursor()
        
        try:
            # Use EXPLAIN QUERY PLAN for readable execution plan
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            result = cursor.fetchall()
            
            lines = ["=" * 80, "EXECUTION PLAN", "=" * 80, ""]
            
            for row in result:
                # SQLite EXPLAIN QUERY PLAN returns: id, parent, notused, detail
                # We're interested in the detail column
                detail = row[3] if len(row) > 3 else str(row)
                lines.append(f"  {detail}")
            
            lines.append("")
            lines.append("Index Usage Tips:")
            lines.append("  - 'SCAN TABLE' = Full table scan (no index used, may be slow)")
            lines.append("  - 'SEARCH TABLE ... USING INDEX' = Index is being used (optimized)")
            lines.append("  - 'USING COVERING INDEX' = Best case, all data from index")
            
            return '\n'.join(lines)
        finally:
            cursor.close()


def create_connector(config: DataSourceConfig) -> DatabaseConnector:
    """
    Factory function to create the appropriate database connector.
    
    Args:
        config: DataSourceConfig with connection details
        
    Returns:
        Appropriate DatabaseConnector subclass instance
        
    Raises:
        ValueError: If database type is not supported
    """
    connectors = {
        'mysql': MySQLConnector,
        'mariadb': MySQLConnector,  # MariaDB uses MySQL protocol
        'postgresql': PostgreSQLConnector,
        'h2': H2Connector,
        'sqlserver': MSSQLConnector,
        'sqlite': SQLiteConnector,
    }
    
    connector_class = connectors.get(config.db_type)
    if not connector_class:
        raise ValueError(f"Unsupported database type: {config.db_type}")
    
    return connector_class(config)
