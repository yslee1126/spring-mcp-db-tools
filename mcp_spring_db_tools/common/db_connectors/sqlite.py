from .base import DatabaseConnector


class SQLiteConnector(DatabaseConnector):
    """SQLite database connector (using Python's built-in sqlite3)."""
    
    def connect(self):
        import sqlite3
        import os
        from pathlib import Path
        
        db_path = self.config.database
        if self.config.url and 'jdbc:sqlite:' in self.config.url:
            db_path = self.config.url.replace('jdbc:sqlite:', '')
        
        if db_path and not os.path.isabs(db_path):
            db_path = os.path.join(self.config.base_path, db_path) if self.config.base_path else os.path.abspath(db_path)
        
        db_path = os.path.expanduser(db_path)
        db_path_obj = Path(db_path)
        if not db_path_obj.exists():
            db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        self._connection = sqlite3.connect(db_path)
        self._connection.row_factory = sqlite3.Row
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get SQLite schema information."""
        schema_info = {'database': self.config.database, 'tables': []}
        cursor = self._connection.cursor()
        
        tables = self._get_tables(cursor, table_name)
        for table_row in tables:
            t_name = table_row['name']
            schema_info['tables'].append({
                'name': t_name, 'comment': None,
                'columns': self._get_columns(cursor, t_name),
                'indexes': self._get_indexes(cursor, t_name),
                'foreign_keys': self._get_foreign_keys(cursor, t_name)
            })
        cursor.close()
        return schema_info

    def _get_tables(self, cursor, table_name: str):
        query = "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        params = []
        if table_name:
            query += " AND name LIKE ?"
            params.append(table_name)
        query += " ORDER BY name"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def _get_columns(self, cursor, table_name: str):
        cursor.execute(f"PRAGMA table_info({table_name})")
        return [{
            'name': col['name'], 'type': col['type'], 'nullable': not col['notnull'],
            'default': col['dflt_value'], 'key': 'PRI' if col['pk'] else '', 'comment': None
        } for col in cursor.fetchall()]

    def _get_indexes(self, cursor, table_name: str):
        cursor.execute(f"PRAGMA index_list({table_name})")
        indexes = []
        for idx in cursor.fetchall():
            cursor.execute(f"PRAGMA index_info({idx['name']})")
            idx_cols = cursor.fetchall()
            indexes.append({
                'name': idx['name'], 'unique': bool(idx['unique']),
                'columns': [col['name'] for col in idx_cols], 'type': 'BTREE'
            })
        return indexes

    def _get_foreign_keys(self, cursor, table_name: str):
        cursor.execute(f"PRAGMA foreign_key_list({table_name})")
        return [{
            'name': f"fk_{table_name}_{fk['id']}", 'column': fk['from'],
            'referenced_table': fk['table'], 'referenced_column': fk['to']
        } for fk in cursor.fetchall()]
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get SQLite stored procedures (Not Supported)."""
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
                params.append(view_name)
            query += " ORDER BY name"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                views.append({'name': row['name'], 'definition': row['sql']})
        finally: cursor.close()
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get SQLite execution plan using EXPLAIN QUERY PLAN."""
        cursor = self._connection.cursor()
        try:
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            result = cursor.fetchall()
            lines = ["=" * 80, "EXECUTION PLAN", "=" * 80, ""]
            for row in result:
                lines.append(f"  {row[3] if len(row) > 3 else str(row)}")
            lines.extend(["", "Index Usage Tips:", "  - 'SCAN TABLE' = Full table scan", "  - 'SEARCH TABLE ... USING INDEX' = Index used", "  - 'USING COVERING INDEX' = Optimized"])
            return '\n'.join(lines)
        finally: cursor.close()
