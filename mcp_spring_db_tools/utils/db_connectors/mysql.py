from .base import DatabaseConnector


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
            tables = self._get_tables(cursor, table_name)
            
            for table in tables:
                table_name_val = table['TABLE_NAME']
                table_info = {
                    'name': table_name_val,
                    'comment': table['TABLE_COMMENT'],
                    'estimated_rows': table['TABLE_ROWS'],
                    'engine': table['ENGINE'],
                    'columns': self._get_columns(cursor, table_name_val),
                    'indexes': self._get_indexes(cursor, table_name_val),
                    'foreign_keys': self._get_foreign_keys(cursor, table_name_val)
                }
                schema_info['tables'].append(table_info)
        
        return schema_info

    def _get_tables(self, cursor, table_name: str):
        query = """
            SELECT TABLE_NAME, TABLE_COMMENT, TABLE_ROWS, ENGINE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE'
        """
        params = [self.config.database]
        if table_name:
            query += " AND TABLE_NAME LIKE %s"
            params.append(table_name)
        query += " ORDER BY TABLE_NAME"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def _get_columns(self, cursor, table_name: str):
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, COLUMN_TYPE, IS_NULLABLE, 
                   COLUMN_DEFAULT, COLUMN_KEY, EXTRA, COLUMN_COMMENT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (self.config.database, table_name))
        return [{
            'name': col['COLUMN_NAME'],
            'type': col['COLUMN_TYPE'],
            'nullable': col['IS_NULLABLE'] == 'YES',
            'default': col['COLUMN_DEFAULT'],
            'key': col['COLUMN_KEY'],
            'extra': col['EXTRA'],
            'comment': col['COLUMN_COMMENT']
        } for col in cursor.fetchall()]

    def _get_indexes(self, cursor, table_name: str):
        cursor.execute("""
            SELECT INDEX_NAME, NON_UNIQUE, GROUP_CONCAT(COLUMN_NAME ORDER BY SEQ_IN_INDEX) as COLUMNS,
                   INDEX_TYPE
            FROM INFORMATION_SCHEMA.STATISTICS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            GROUP BY INDEX_NAME, NON_UNIQUE, INDEX_TYPE
            ORDER BY INDEX_NAME
        """, (self.config.database, table_name))
        return [{
            'name': idx['INDEX_NAME'],
            'unique': idx['NON_UNIQUE'] == 0,
            'columns': idx['COLUMNS'].split(','),
            'type': idx['INDEX_TYPE']
        } for idx in cursor.fetchall()]

    def _get_foreign_keys(self, cursor, table_name: str):
        cursor.execute("""
            SELECT CONSTRAINT_NAME, COLUMN_NAME, 
                   REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME
            FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            AND REFERENCED_TABLE_NAME IS NOT NULL
            ORDER BY CONSTRAINT_NAME, ORDINAL_POSITION
        """, (self.config.database, table_name))
        return [{
            'name': fk['CONSTRAINT_NAME'],
            'column': fk['COLUMN_NAME'],
            'referenced_table': fk['REFERENCED_TABLE_NAME'],
            'referenced_column': fk['REFERENCED_COLUMN_NAME']
        } for fk in cursor.fetchall()]
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get MySQL stored procedures."""
        procedures = []
        with self._connection.cursor() as cursor:
            query = """
                SELECT ROUTINE_NAME, ROUTINE_DEFINITION, ROUTINE_COMMENT
                FROM INFORMATION_SCHEMA.ROUTINES
                WHERE ROUTINE_SCHEMA = %s AND ROUTINE_TYPE = 'PROCEDURE'
            """
            params = [self.config.database]
            if procedure_name:
                query += " AND ROUTINE_NAME LIKE %s"
                params.append(procedure_name)
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
                params.append(view_name)
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
            try:
                cursor.execute(f"EXPLAIN ANALYZE {query}")
                result = cursor.fetchall()
                return self._format_explain_result(result, 'analyze')
            except Exception:
                cursor.execute(f"EXPLAIN {query}")
                result = cursor.fetchall()
                return self._format_explain_result(result, 'basic')
    
    def _format_explain_result(self, result: list, mode: str) -> str:
        """Format EXPLAIN result for display."""
        if mode == 'analyze':
            return '\n'.join([str(row) for row in result])
        
        lines = ["=" * 80, "EXECUTION PLAN", "=" * 80]
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
