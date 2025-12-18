"""벡터 검색"""

from typing import List, Optional, Dict, Any
import json

from src.core.models import (
    QueryRequest,
    RetrievalResult,
    RetrievalResponse,
    EndpointChunk,
    ChunkMetadata,
)
from src.core.config import settings
from src.ingestion.indexer import ChromaIndexer
from src.core.exceptions import RetrievalError


class VectorSearcher:
    """ChromaDB 벡터 검색"""

    def __init__(self, collection_name: str = None):
        """
        Args:
            collection_name: 컬렉션 이름
        """
        try:
            self.indexer = ChromaIndexer(collection_name=collection_name)
        except Exception as e:
            raise RetrievalError(f"Failed to initialize searcher: {e}")

    def search(
        self,
        query_embedding: List[float],
        query_request: QueryRequest
    ) -> RetrievalResponse:
        """벡터 유사도 검색

        Args:
            query_embedding: 질의 임베딩
            query_request: 질의 요청

        Returns:
            RetrievalResponse: 검색 결과

        Raises:
            RetrievalError: 검색 실패 시
        """
        try:
            # 메타데이터 필터 변환
            where = self._build_where_clause(query_request.filters)

            # ChromaDB 검색
            results = self.indexer.search(
                query_embedding=query_embedding,
                top_k=query_request.top_k,
                where=where
            )

            # 결과 변환
            retrieval_results = self._parse_results(results, query_request.query)

            return RetrievalResponse(
                results=retrieval_results,
                query=query_request.query,
                total_results=len(retrieval_results)
            )

        except Exception as e:
            raise RetrievalError(f"Search failed: {e}")

    def _build_where_clause(
        self,
        filters: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """메타데이터 필터 조건 생성

        Args:
            filters: 필터 딕셔너리

        Returns:
            Optional[Dict[str, Any]]: ChromaDB where 조건
        """
        if not filters:
            return None

        conditions = []

        # method 필터
        if "method" in filters:
            conditions.append({"method": {"$eq": filters["method"]}})

        # tags 필터 (문자열 포함 검색은 지원하지 않으므로 제거하거나 정확한 일치만 사용)
        # ChromaDB의 제한으로 인해 tags 필터는 현재 비활성화
        # if "tags" in filters:
        #     conditions.append({"tags": {"$eq": filters["tags"]}})

        # requires_auth 필터
        if "requires_auth" in filters:
            conditions.append({"requires_auth": {"$eq": filters["requires_auth"]}})

        # content_type 필터
        if "content_type" in filters:
            conditions.append({"content_type": {"$eq": filters["content_type"]}})

        # 조건이 없으면 None
        if not conditions:
            return None

        # 조건이 하나면 그대로, 여러개면 $and로 결합
        if len(conditions) == 1:
            return conditions[0]
        else:
            return {"$and": conditions}

    def _parse_results(
        self,
        chroma_results: Dict[str, Any],
        query: str
    ) -> List[RetrievalResult]:
        """ChromaDB 결과를 RetrievalResult로 변환

        Args:
            chroma_results: ChromaDB 검색 결과
            query: 원본 질의

        Returns:
            List[RetrievalResult]: 변환된 결과 리스트
        """
        retrieval_results = []

        # ChromaDB 결과 구조: {'ids': [[...]], 'distances': [[...]], 'metadatas': [[...]], 'documents': [[...]]}
        ids = chroma_results.get("ids", [[]])[0]
        distances = chroma_results.get("distances", [[]])[0]
        metadatas = chroma_results.get("metadatas", [[]])[0]
        documents = chroma_results.get("documents", [[]])[0]

        for rank, (chunk_id, distance, metadata, document) in enumerate(
            zip(ids, distances, metadatas, documents), start=1
        ):
            # Distance를 유사도로 변환 (cosine distance: 0=identical, 2=opposite)
            # Similarity = 1 - (distance / 2)
            similarity_score = 1.0 - (distance / 2.0)

            # 유사도 임계값 체크
            if similarity_score < settings.SIMILARITY_THRESHOLD:
                continue

            # EndpointChunk 재구성
            chunk = self._reconstruct_chunk(chunk_id, metadata, document)

            retrieval_results.append(
                RetrievalResult(
                    chunk=chunk,
                    similarity_score=similarity_score,
                    rank=rank
                )
            )

        return retrieval_results

    def _reconstruct_chunk(
        self,
        chunk_id: str,
        metadata: Dict[str, Any],
        document: str
    ) -> EndpointChunk:
        """메타데이터에서 EndpointChunk 재구성

        Args:
            chunk_id: 청크 ID
            metadata: ChromaDB 메타데이터
            document: 문서 텍스트

        Returns:
            EndpointChunk: 재구성된 청크
        """
        # method와 path 추출
        method = metadata.get("method", "")
        endpoint = metadata.get("endpoint", "")

        # tags 파싱 (문자열 → 리스트)
        tags_str = metadata.get("tags", "")
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        # ChunkMetadata 생성
        chunk_metadata = ChunkMetadata(
            endpoint=endpoint,
            method=method,
            tags=tags,
            operation_id=metadata.get("operation_id") or None,
            requires_auth=metadata.get("requires_auth", False),
            content_type=metadata.get("content_type", "application/json")
        )

        # EndpointChunk 생성 (최소 정보만)
        chunk = EndpointChunk(
            chunk_id=chunk_id,
            method=method,
            path=endpoint,
            summary=metadata.get("summary") or None,
            description=None,  # 전체 정보는 나중에 필요시 로드
            parameters=[],
            request_body=None,
            responses={},
            metadata=chunk_metadata
        )

        return chunk

    def get_chunk_by_id(self, chunk_id: str) -> Optional[EndpointChunk]:
        """ID로 청크 조회

        Args:
            chunk_id: 청크 ID

        Returns:
            Optional[EndpointChunk]: 청크 (없으면 None)
        """
        # TODO: 전체 청크 정보를 별도 저장소에서 로드
        # 현재는 메타데이터만 반환
        pass
