from .base import DatabaseConnector


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
        schema_info = {'database': self.config.database, 'tables': []}
        
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
            tables = self._get_tables(cursor, table_name)
            for table in tables:
                t_name = table['table_name']
                schema_info['tables'].append({
                    'name': t_name,
                    'comment': table['table_comment'],
                    'estimated_rows': table['estimated_rows'],
                    'columns': self._get_columns(cursor, t_name),
                    'indexes': self._get_indexes(cursor, t_name),
                    'foreign_keys': self._get_foreign_keys(cursor, t_name)
                })
        return schema_info

    def _get_tables(self, cursor, table_name: str):
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
            params.append(table_name)
        query += " ORDER BY t.table_name"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def _get_columns(self, cursor, table_name: str):
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
        """, (table_name, table_name))
        return [{
            'name': col['column_name'],
            'type': col['udt_name'],
            'nullable': col['is_nullable'] == 'YES',
            'default': col['column_default'],
            'key': col['column_key'],
            'comment': col['column_comment']
        } for col in cursor.fetchall()]

    def _get_indexes(self, cursor, table_name: str):
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
        """, (table_name,))
        return [{
            'name': idx['index_name'],
            'unique': idx['is_unique'],
            'columns': idx['columns'],
            'type': idx['index_type']
        } for idx in cursor.fetchall()]

    def _get_foreign_keys(self, cursor, table_name: str):
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
        """, (table_name,))
        return [{
            'name': fk['constraint_name'],
            'column': fk['column_name'],
            'referenced_table': fk['referenced_table'],
            'referenced_column': fk['referenced_column']
        } for fk in cursor.fetchall()]

    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get PostgreSQL stored procedures."""
        import psycopg2.extras
        procedures = []
        with self._connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cursor:
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
                params.append(procedure_name)
            query += " ORDER BY p.proname"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                procedures.append({
                    'name': row['name'], 'definition': row['definition'], 'comment': row['comment']
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
                params.append(view_name)
            query += " ORDER BY table_name"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                views.append({'name': row['table_name'], 'definition': row['view_definition']})
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
