"""질의 처리기"""

from typing import List, Optional, Dict, Any
from src.core.models import QueryRequest
from src.core.config import settings
from src.ingestion.embedder import OllamaEmbedder
from src.core.exceptions import RetrievalError


class QueryProcessor:
    """사용자 질의 처리"""

    def __init__(self):
        """Query Processor 초기화"""
        self.embedder = OllamaEmbedder()

    def process_query(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        top_k: int = None
    ) -> QueryRequest:
        """질의 처리 및 정규화

        Args:
            query: 사용자 질의
            filters: 메타데이터 필터
            top_k: 검색할 개수

        Returns:
            QueryRequest: 처리된 질의

        Raises:
            RetrievalError: 처리 실패 시
        """
        if not query or not query.strip():
            raise RetrievalError("Query cannot be empty")

        # 질의 정규화
        normalized_query = self._normalize_query(query)

        # 필터 추출 (질의에서 자동 감지)
        auto_filters = self._extract_filters(normalized_query)

        # 사용자 필터와 자동 필터 병합
        merged_filters = {**(filters or {}), **auto_filters}

        return QueryRequest(
            query=normalized_query,
            filters=merged_filters if merged_filters else None,
            top_k=top_k or settings.TOP_K
        )

    def embed_query(self, query: str) -> List[float]:
        """질의 임베딩 생성

        Args:
            query: 질의 문자열

        Returns:
            List[float]: 임베딩 벡터

        Raises:
            RetrievalError: 임베딩 생성 실패 시
        """
        try:
            return self.embedder.embed_text(query)
        except Exception as e:
            raise RetrievalError(f"Failed to embed query: {e}")

    def _normalize_query(self, query: str) -> str:
        """질의 정규화

        Args:
            query: 원본 질의

        Returns:
            str: 정규화된 질의
        """
        # 양쪽 공백 제거
        query = query.strip()

        # 여러 공백을 하나로
        query = " ".join(query.split())

        return query

    def _extract_filters(self, query: str) -> Dict[str, Any]:
        """질의에서 필터 자동 추출

        Args:
            query: 정규화된 질의

        Returns:
            Dict[str, Any]: 추출된 필터
        """
        filters = {}
        query_lower = query.lower()

        # HTTP 메서드 감지
        method_keywords = {
            "post": ["등록", "생성", "추가", "post", "create"],
            "get": ["조회", "확인", "검색", "get", "read", "fetch"],
            "put": ["수정", "변경", "업데이트", "put", "update"],
            "delete": ["삭제", "제거", "취소", "delete", "remove", "cancel"],
            "patch": ["일부수정", "patch"],
        }

        for method, keywords in method_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                filters["method"] = method.upper()
                break

        # 태그 감지 (도메인별)
        tag_keywords = {
            "payment": ["결제", "payment", "pay"],
            "user": ["사용자", "유저", "회원", "user", "member"],
            "order": ["주문", "order"],
            "product": ["상품", "제품", "product", "item"],
        }

        for tag, keywords in tag_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                # tags는 contains 쿼리로 처리
                if "tags" not in filters:
                    filters["tags"] = tag
                break

        return filters
