"""
Execution plan tool.
Provides SQL query execution plan analysis functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_spring_db_tools.utils.db_connector import DatabaseConnector


# Allowed query types for execution plan
ALLOWED_QUERY_STARTS = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH')


def validate_query(query: str) -> tuple[bool, str]:
    """
    Validate that the query is allowed for execution plan analysis.
    
    Args:
        query: SQL query to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    query_upper = query.strip().upper()
    
    if not any(query_upper.startswith(start) for start in ALLOWED_QUERY_STARTS):
        return False, (
            "Error: Only SELECT, INSERT, UPDATE, DELETE, and WITH queries are allowed. "
            "DDL statements (CREATE, DROP, ALTER, TRUNCATE) are not permitted for EXPLAIN."
        )
    
    return True, ""


def get_execution_plan(connector: "DatabaseConnector", query: str) -> str:
    """
    Get execution plan for a SQL query.
    
    Args:
        connector: Database connector instance
        query: SQL query to analyze
        
    Returns:
        Execution plan as formatted string
    """
    # Validate query
    is_valid, error_message = validate_query(query)
    if not is_valid:
        return error_message
    
    with connector.connection_context():
        return connector.get_execution_plan(query)


def format_execution_plan_result(ds_name: str, query: str, plan: str) -> str:
    """
    Format execution plan result with metadata.
    
    Args:
        ds_name: Datasource name
        query: Original SQL query
        plan: Execution plan string
        
    Returns:
        Formatted result string
    """
    query_preview = query[:200] + '...' if len(query) > 200 else query
    
    improvement_guide = """
쿼리 개선 가이드

다음 항목들을 검토하여 쿼리 성능을 최적화하세요:

1. 스캔 방식 최적화
   - Full Table Scan은 위험합니다
   - Index Full Scan이 차선책이지만 가능하면 Index Range Scan을 할 수 있는지 검토하세요
   
2. 인덱스 활용
   - 복합 인덱스의 선행 컬럼이 조건절에 없는 경우 더 좋은 방안을 검토하세요
   - 정렬 조건을 인덱스로 활용할 수 없는 경우 더 좋은 방안을 검토하세요
   
3. 조인 최적화
   - 조인 순서가 작은 테이블부터가 아니라면 더 좋은 방안을 검토하세요
   - LEFT JOIN이 너무 많아서 실행계획이 잘 안 풀리는 경우, 쿼리를 둘로 나눠서 
     첫 번째 쿼리 결과를 두 번째 쿼리에 공급하는 방식으로 개선할 수 있는지 검토하세요
   
4. SELECT 절 최적화
   - 너무 많은 컬럼을 SELECT한 경우 꼭 필요한 것인지 검토하세요
   
5. 쿼리 구문 최적화
   - Function 사용, 컬럼 가공, 컬럼 타입 불일치 같은 구문이 쿼리를 무겁게 하는지 검토하세요
   - 조건절에 %LIKE%, OR 조건 등 성능에 부정적인 구문을 없앨 수 있는지 검토하세요

6. 개선 방안 제안
위 항목들을 기반으로 다음과 같은 방법으로 개선 방안을 제안해주세요:
- 쿼리 변경 (WHERE 절, JOIN 순서, SELECT 컬럼 등)
- 다른 인덱스 추천 (기존 인덱스 중 더 효율적인 것)
- 신규 인덱스 추가 (새로운 인덱스 생성 제안)
- 힌트 추가 (데이터베이스 힌트를 통한 실행계획 조정)
"""
    
    return "\n".join([
        f"Datasource: {ds_name}",
        f"Query: {query_preview}",
        "",
        plan,
        "",
        "=" * 80,
        improvement_guide
    ])
