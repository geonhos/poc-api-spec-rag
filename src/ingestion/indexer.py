"""ChromaDB 인덱서"""

from typing import List, Dict, Any
import chromadb
from chromadb.config import Settings as ChromaSettings

from src.core.models import EndpointChunk
from src.core.config import settings
from src.core.exceptions import VectorStoreError


class ChromaIndexer:
    """ChromaDB 벡터 저장소 인덱서"""

    def __init__(self, collection_name: str = None, reset: bool = False):
        """
        Args:
            collection_name: 컬렉션 이름 (기본값: settings.CHROMA_COLLECTION_NAME)
            reset: True이면 기존 컬렉션 삭제 후 재생성
        """
        self.collection_name = collection_name or settings.CHROMA_COLLECTION_NAME

        try:
            # ChromaDB 클라이언트 생성
            self.client = chromadb.PersistentClient(
                path=str(settings.CHROMA_DB_DIR)
            )

            # 컬렉션 초기화
            if reset:
                try:
                    self.client.delete_collection(name=self.collection_name)
                except Exception:
                    pass  # 컬렉션이 없으면 무시

            # 컬렉션 생성 또는 가져오기
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={
                    "embedding_model": settings.OLLAMA_EMBEDDING_MODEL,
                    "distance_metric": settings.CHROMA_DISTANCE_METRIC,
                }
            )

        except Exception as e:
            raise VectorStoreError(f"Failed to initialize ChromaDB: {e}")

    def index_chunks(
        self,
        chunks: List[EndpointChunk],
        embeddings: List[List[float]]
    ) -> None:
        """청크와 임베딩을 ChromaDB에 저장

        Args:
            chunks: 엔드포인트 청크 리스트
            embeddings: 임베딩 벡터 리스트

        Raises:
            VectorStoreError: 저장 실패 시
        """
        if len(chunks) != len(embeddings):
            raise VectorStoreError(
                f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) "
                "count mismatch"
            )

        if not chunks:
            return

        try:
            # 데이터 준비
            ids = [chunk.chunk_id for chunk in chunks]
            documents = [chunk.to_embedding_text() for chunk in chunks]
            metadatas = [self._chunk_to_metadata(chunk) for chunk in chunks]

            # ChromaDB에 저장
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

        except Exception as e:
            raise VectorStoreError(f"Failed to index chunks: {e}")

    def _chunk_to_metadata(self, chunk: EndpointChunk) -> Dict[str, Any]:
        """청크를 ChromaDB 메타데이터로 변환

        Args:
            chunk: 엔드포인트 청크

        Returns:
            Dict[str, Any]: ChromaDB 메타데이터
        """
        return {
            "endpoint": chunk.metadata.endpoint,
            "method": chunk.metadata.method,
            "tags": ",".join(chunk.metadata.tags),  # 리스트를 문자열로
            "operation_id": chunk.metadata.operation_id or "",
            "requires_auth": chunk.metadata.requires_auth,
            "content_type": chunk.metadata.content_type or "application/json",
            "summary": chunk.summary or "",
        }

    def get_collection_info(self) -> Dict[str, Any]:
        """컬렉션 정보 조회

        Returns:
            Dict[str, Any]: 컬렉션 정보
        """
        try:
            count = self.collection.count()
            metadata = self.collection.metadata

            return {
                "name": self.collection_name,
                "count": count,
                "metadata": metadata,
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to get collection info: {e}")

    def delete_collection(self) -> None:
        """컬렉션 삭제

        Raises:
            VectorStoreError: 삭제 실패 시
        """
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception as e:
            raise VectorStoreError(f"Failed to delete collection: {e}")

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """유사도 검색

        Args:
            query_embedding: 질의 임베딩 벡터
            top_k: 검색할 개수
            where: 메타데이터 필터

        Returns:
            Dict[str, Any]: 검색 결과

        Raises:
            VectorStoreError: 검색 실패 시
        """
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where
            )

            return results

        except Exception as e:
            raise VectorStoreError(f"Failed to search: {e}")
