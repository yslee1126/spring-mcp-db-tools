from .base import DatabaseConnector


class H2Connector(DatabaseConnector):
    """H2 database connector (TCP mode only for external connections)."""
    
    def connect(self):
        if self.config.host in ('file', 'mem'):
            raise ConnectionError(
                "H2 embedded mode (file: or mem:) cannot be accessed externally. "
                "Please configure H2 with TCP server mode for MCP access."
            )
        try:
            import jaydebeapi
            self._connection = jaydebeapi.connect(
                'org.h2.Driver', self.config.url,
                [self.config.username, self.config.password],
                self.config.driver_path or '/path/to/h2.jar'
            )
        except ImportError:
            raise ConnectionError("H2 database requires jaydebeapi. Install with: pip install jaydebeapi")
    
    def disconnect(self):
        if self._connection:
            self._connection.close()
            self._connection = None
    
    def get_schema_info(self, table_name: str = "") -> dict:
        """Get H2 schema information."""
        schema_info = {'database': self.config.database, 'tables': []}
        cursor = self._connection.cursor()
        try:
            tables = self._get_tables(cursor, table_name)
            for table in tables:
                t_name = table[0]
                schema_info['tables'].append({
                    'name': t_name, 'comment': table[1],
                    'columns': self._get_columns(cursor, t_name),
                    'indexes': self._get_indexes(cursor, t_name)
                })
        finally: cursor.close()
        return schema_info

    def _get_tables(self, cursor, table_name: str):
        query = "SELECT TABLE_NAME, REMARKS FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_TYPE = 'TABLE'"
        params = []
        if table_name:
            query += " AND TABLE_NAME LIKE ?"
            params.append(table_name)
        query += " ORDER BY TABLE_NAME"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def _get_columns(self, cursor, table_name: str):
        cursor.execute("SELECT COLUMN_NAME, TYPE_NAME, IS_NULLABLE, COLUMN_DEFAULT, REMARKS FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION", (table_name,))
        return [{
            'name': col[0], 'type': col[1], 'nullable': col[2] == 'YES',
            'default': col[3], 'comment': col[4]
        } for col in cursor.fetchall()]

    def _get_indexes(self, cursor, table_name: str):
        cursor.execute("SELECT INDEX_NAME, NON_UNIQUE, COLUMN_NAME FROM INFORMATION_SCHEMA.INDEXES WHERE TABLE_SCHEMA = 'PUBLIC' AND TABLE_NAME = ? ORDER BY INDEX_NAME, ORDINAL_POSITION", (table_name,))
        idx_map = {}
        for idx in cursor.fetchall():
            if idx[0] not in idx_map:
                idx_map[idx[0]] = {'name': idx[0], 'unique': idx[1] == 0, 'columns': []}
            idx_map[idx[0]]['columns'].append(idx[2])
        return list(idx_map.values())
    
    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get H2 stored procedures (Function Aliases)."""
        procedures = []
        cursor = self._connection.cursor()
        try:
            query = "SELECT ALIAS_NAME, JAVA_CLASS, METHOD_NAME FROM INFORMATION_SCHEMA.FUNCTION_ALIASES WHERE ALIAS_SCHEMA = 'PUBLIC'"
            params = []
            if procedure_name:
                query += " AND ALIAS_NAME LIKE ?"
                params.append(procedure_name)
            query += " ORDER BY ALIAS_NAME"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                procedures.append({'name': row[0], 'definition': f"Java Class: {row[1]}, Method: {row[2]}"})
        except: pass
        finally: cursor.close()
        return {'database': self.config.database, 'procedures': procedures}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get H2 views."""
        views = []
        cursor = self._connection.cursor()
        try:
            query = "SELECT TABLE_NAME, VIEW_DEFINITION FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA = 'PUBLIC'"
            params = []
            if view_name:
                query += " AND TABLE_NAME LIKE ?"
                params.append(view_name)
            query += " ORDER BY TABLE_NAME"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                views.append({'name': row[0], 'definition': row[1]})
        finally: cursor.close()
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get H2 execution plan using EXPLAIN."""
        cursor = self._connection.cursor()
        try:
            cursor.execute(f"EXPLAIN {query}")
            result = cursor.fetchall()
            return "================================================================================\nEXECUTION PLAN\n================================================================================\n\n" + "\n".join([str(row[0]) for row in result])
        finally: cursor.close()
