"""Ollama 임베딩 생성기"""

from typing import List
import ollama

from src.core.models import EndpointChunk
from src.core.config import settings
from src.core.exceptions import EmbeddingError, OllamaConnectionError


class OllamaEmbedder:
    """Ollama를 사용한 임베딩 생성"""

    def __init__(self, model: str = None):
        """
        Args:
            model: 임베딩 모델 이름 (기본값: settings.OLLAMA_EMBEDDING_MODEL)
        """
        self.model = model or settings.OLLAMA_EMBEDDING_MODEL

    def embed_chunk(self, chunk: EndpointChunk) -> List[float]:
        """단일 청크 임베딩 생성

        Args:
            chunk: 엔드포인트 청크

        Returns:
            List[float]: 임베딩 벡터

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
        """
        text = chunk.to_embedding_text()
        return self.embed_text(text)

    def embed_chunks(self, chunks: List[EndpointChunk]) -> List[List[float]]:
        """여러 청크 배치 임베딩 생성

        Args:
            chunks: 엔드포인트 청크 리스트

        Returns:
            List[List[float]]: 임베딩 벡터 리스트

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
        """
        texts = [chunk.to_embedding_text() for chunk in chunks]
        return self.embed_batch(texts)

    def embed_text(self, text: str) -> List[float]:
        """단일 텍스트 임베딩 생성

        Args:
            text: 임베딩할 텍스트

        Returns:
            List[float]: 임베딩 벡터

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
            OllamaConnectionError: Ollama 연결 실패 시
        """
        try:
            response = ollama.embed(
                model=self.model,
                input=text
            )

            embeddings = response.get("embeddings")
            if not embeddings or len(embeddings) == 0:
                raise EmbeddingError("No embeddings returned from Ollama")

            return embeddings[0]

        except ConnectionError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama: {e}. "
                "Make sure Ollama is running (ollama serve)"
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embedding: {e}")

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """여러 텍스트 배치 임베딩 생성

        Args:
            texts: 임베딩할 텍스트 리스트

        Returns:
            List[List[float]]: 임베딩 벡터 리스트

        Raises:
            EmbeddingError: 임베딩 생성 실패 시
            OllamaConnectionError: Ollama 연결 실패 시
        """
        if not texts:
            return []

        try:
            response = ollama.embed(
                model=self.model,
                input=texts
            )

            embeddings = response.get("embeddings")
            if not embeddings:
                raise EmbeddingError("No embeddings returned from Ollama")

            if len(embeddings) != len(texts):
                raise EmbeddingError(
                    f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                )

            return embeddings

        except ConnectionError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama: {e}. "
                "Make sure Ollama is running (ollama serve)"
            )
        except Exception as e:
            raise EmbeddingError(f"Failed to generate embeddings: {e}")

    def get_embedding_dimension(self) -> int:
        """임베딩 차원 확인

        Returns:
            int: 임베딩 벡터 차원

        Raises:
            EmbeddingError: 차원 확인 실패 시
        """
        try:
            # 테스트 텍스트로 임베딩 생성
            test_embedding = self.embed_text("test")
            return len(test_embedding)
        except Exception as e:
            raise EmbeddingError(f"Failed to get embedding dimension: {e}")
