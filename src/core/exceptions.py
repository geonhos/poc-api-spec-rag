"""커스텀 예외 정의"""


class APISpecRAGError(Exception):
    """Base exception for API Spec RAG"""
    pass


class SpecParsingError(APISpecRAGError):
    """OpenAPI 명세서 파싱 오류"""
    pass


class ChunkingError(APISpecRAGError):
    """청킹 처리 오류"""
    pass


class EmbeddingError(APISpecRAGError):
    """임베딩 생성 오류"""
    pass


class VectorStoreError(APISpecRAGError):
    """벡터 저장소 오류"""
    pass


class RetrievalError(APISpecRAGError):
    """검색 오류"""
    pass


class GenerationError(APISpecRAGError):
    """cURL 생성 오류"""
    pass


class ValidationError(APISpecRAGError):
    """검증 오류"""
    pass


class OllamaConnectionError(APISpecRAGError):
    """Ollama 연결 오류"""
    pass


class InsufficientInformationError(APISpecRAGError):
    """명세서 정보 부족 오류"""
    def __init__(self, missing_info: str):
        self.missing_info = missing_info
        super().__init__(f"Insufficient information: {missing_info}")
