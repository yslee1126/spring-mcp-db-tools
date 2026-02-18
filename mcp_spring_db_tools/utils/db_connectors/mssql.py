from .base import DatabaseConnector


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
        schema_info = {'database': self.config.database, 'tables': []}
        
        with self._connection.cursor() as cursor:
            tables = self._get_tables(cursor, table_name)
            for table in tables:
                s_name = table['TABLE_SCHEMA']
                t_name = table['TABLE_NAME']
                schema_info['tables'].append({
                    'name': t_name,
                    'schema': s_name,
                    'comment': None,
                    'estimated_rows': None,
                    'columns': self._get_columns(cursor, s_name, t_name),
                    'indexes': self._get_indexes(cursor, s_name, t_name),
                    'foreign_keys': self._get_foreign_keys(cursor, s_name, t_name)
                })
        return schema_info

    def _get_tables(self, cursor, table_name: str):
        query = """
            SELECT TABLE_SCHEMA, TABLE_NAME, TABLE_TYPE
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
        """
        params = []
        if table_name:
            query += " AND TABLE_NAME LIKE %s"
            params.append(table_name)
        query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
        cursor.execute(query, tuple(params))
        return cursor.fetchall()

    def _get_columns(self, cursor, schema_name, table_name):
        cursor.execute("""
            SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH,
                   NUMERIC_PRECISION, NUMERIC_SCALE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
        """, (schema_name, table_name))
        cols = []
        for col in cursor.fetchall():
            dt = col['DATA_TYPE']
            if col['CHARACTER_MAXIMUM_LENGTH']:
                dt += "(MAX)" if col['CHARACTER_MAXIMUM_LENGTH'] == -1 else f"({col['CHARACTER_MAXIMUM_LENGTH']})"
            elif col['NUMERIC_PRECISION']:
                dt += f"({col['NUMERIC_PRECISION']},{col['NUMERIC_SCALE']})" if col['NUMERIC_SCALE'] else f"({col['NUMERIC_PRECISION']})"
            cols.append({
                'name': col['COLUMN_NAME'], 'type': dt, 'nullable': col['IS_NULLABLE'] == 'YES',
                'default': col['COLUMN_DEFAULT'], 'comment': None
            })
        return cols

    def _get_indexes(self, cursor, schema_name, table_name):
        indexes = []
        # Primary Keys
        try:
            cursor.execute("""
                SELECT kcu.COLUMN_NAME, tc.CONSTRAINT_NAME
                FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON tc.CONSTRAINT_NAME = kcu.CONSTRAINT_NAME
                    AND tc.TABLE_SCHEMA = kcu.TABLE_SCHEMA AND tc.TABLE_NAME = kcu.TABLE_NAME
                WHERE tc.TABLE_SCHEMA = %s AND tc.TABLE_NAME = %s AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                ORDER BY kcu.ORDINAL_POSITION
            """, (schema_name, table_name))
            pk_rows = cursor.fetchall()
            if pk_rows:
                indexes.append({
                    'name': pk_rows[0]['CONSTRAINT_NAME'], 'unique': True,
                    'columns': [r['COLUMN_NAME'] for r in pk_rows], 'type': 'PRIMARY KEY'
                })
        except: pass

        # Regular Indexes
        try:
            cursor.execute("""
                SELECT i.name AS INDEX_NAME, i.type_desc AS INDEX_TYPE, i.is_unique,
                       COL_NAME(ic.object_id, ic.column_id) AS COLUMN_NAME, ic.is_descending_key
                FROM sys.indexes i
                JOIN sys.index_columns ic ON i.object_id = ic.object_id AND i.index_id = ic.index_id
                WHERE OBJECT_SCHEMA_NAME(i.object_id) = %s AND OBJECT_NAME(i.object_id) = %s
                    AND i.type > 0 AND i.is_primary_key = 0
                ORDER BY i.name, ic.key_ordinal
            """, (schema_name, table_name))
            idx_map = {}
            for row in cursor.fetchall():
                iname = row['INDEX_NAME']
                if iname not in idx_map:
                    idx_map[iname] = {'name': iname, 'unique': row['is_unique'], 'type': row['INDEX_TYPE'], 'columns': []}
                idx_map[iname]['columns'].append(f"{row['COLUMN_NAME']} DESC" if row['is_descending_key'] else row['COLUMN_NAME'])
            indexes.extend(list(idx_map.values()))
        except: pass
        return indexes

    def _get_foreign_keys(self, cursor, schema_name, table_name):
        try:
            cursor.execute("""
                SELECT fk.name AS FK_NAME, COL_NAME(fkc.parent_object_id, fkc.parent_column_id) AS COLUMN_NAME,
                       OBJECT_SCHEMA_NAME(fk.referenced_object_id) AS REF_SCHEMA, OBJECT_NAME(fk.referenced_object_id) AS REF_TABLE,
                       COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id) AS REF_COLUMN
                FROM sys.foreign_keys fk
                JOIN sys.foreign_key_columns fkc ON fk.object_id = fkc.constraint_object_id
                WHERE OBJECT_SCHEMA_NAME(fk.parent_object_id) = %s AND OBJECT_NAME(fk.parent_object_id) = %s
                ORDER BY fk.name, fkc.constraint_column_id
            """, (schema_name, table_name))
            return [{
                'name': r['FK_NAME'], 'column': r['COLUMN_NAME'],
                'referenced_table': f"{r['REF_SCHEMA']}.{r['REF_TABLE']}", 'referenced_column': r['REF_COLUMN']
            } for r in cursor.fetchall()]
        except: return []

    def get_procedures_info(self, procedure_name: str = "") -> dict:
        """Get MSSQL stored procedures."""
        procedures = []
        with self._connection.cursor() as cursor:
            query = "SELECT ROUTINE_SCHEMA, ROUTINE_NAME, ROUTINE_DEFINITION FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_TYPE = 'PROCEDURE'"
            params = []
            if procedure_name:
                query += " AND ROUTINE_NAME LIKE %s"
                params.append(procedure_name)
            query += " ORDER BY ROUTINE_SCHEMA, ROUTINE_NAME"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                procedures.append({'schema': row['ROUTINE_SCHEMA'], 'name': row['ROUTINE_NAME'], 'definition': row['ROUTINE_DEFINITION']})
        return {'database': self.config.database, 'procedures': procedures}

    def get_views_info(self, view_name: str = "") -> dict:
        """Get MSSQL views."""
        views = []
        with self._connection.cursor() as cursor:
            query = "SELECT TABLE_SCHEMA, TABLE_NAME, VIEW_DEFINITION FROM INFORMATION_SCHEMA.VIEWS"
            params = []
            if view_name:
                query += " WHERE TABLE_NAME LIKE %s"
                params.append(view_name)
            query += " ORDER BY TABLE_SCHEMA, TABLE_NAME"
            cursor.execute(query, tuple(params))
            for row in cursor.fetchall():
                views.append({'schema': row['TABLE_SCHEMA'], 'name': row['TABLE_NAME'], 'definition': row['VIEW_DEFINITION']})
        return {'database': self.config.database, 'views': views}

    def get_execution_plan(self, query: str) -> str:
        """Get MSSQL execution plan."""
        with self._connection.cursor() as cursor:
            try:
                cursor.execute("SET SHOWPLAN_TEXT ON")
                cursor.execute(query)

                # pymssql은 SET SHOWPLAN_TEXT ON 실행 후 실행계획이
                # 여러 결과셋으로 분리될 수 있으므로 nextset()으로 모두 수집
                plan_lines = []
                while True:
                    rows = cursor.fetchall()
                    if rows:
                        for r in rows:
                            if 'StmtText' in r and r['StmtText']:
                                plan_lines.append(r['StmtText'])
                    if not cursor.nextset():
                        break

                cursor.execute("SET SHOWPLAN_TEXT OFF")

                if plan_lines:
                    return (
                        "================================================================================\n"
                        "EXECUTION PLAN\n"
                        "================================================================================\n\n"
                        + "\n".join(plan_lines)
                    )
                else:
                    return (
                        "================================================================================\n"
                        "EXECUTION PLAN\n"
                        "================================================================================\n\n"
                        "(실행계획 결과가 비어 있습니다. SHOWPLAN 권한을 확인하거나 쿼리를 점검하세요.)"
                    )
            except Exception as e:
                try:
                    cursor.execute("SET SHOWPLAN_TEXT OFF")
                except Exception:
                    pass
                if "SHOWPLAN permission denied" in str(e) or "262" in str(e):
                    return (
                        "================================================================================\n"
                        "⚠️ 실행 계획 권한 부족 (Permission Denied)\n"
                        "================================================================================\n\n"
                        "현재 데이터베이스 사용자에게 'SHOWPLAN' 권한이 없어 실행 계획을 직접 추출할 수 없습니다.\n\n"
                        "💡 대안 및 권장 사항:\n"
                        "1. 테이블 스키마 조회 (`get_schema_info`)를 통해 인덱스 정보를 확인하세요.\n"
                        "2. 쿼리 최적화 팁: SELECT * 자제, LIKE '%keyword%' 주의 등."
                    )
                raise e
