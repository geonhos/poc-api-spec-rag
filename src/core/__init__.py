"""Core module - 공통 모델, 설정, 예외"""

from .models import (
    # OpenAPI Models
    OpenAPISpec,
    PathItem,
    Operation,
    Parameter,
    RequestBody,
    Response,
    Schema,
    # RAG Models
    EndpointChunk,
    ChunkMetadata,
    # Query Models
    QueryRequest,
    RetrievalResult,
    RetrievalResponse,
    # Generation Models
    CurlCommand,
    GenerationRequest,
    GenerationResponse,
    # Validation Models
    ValidationResult,
    ValidationError,
    ConfidenceScore,
    # Pipeline Models
    PipelineRequest,
    PipelineResponse,
)
from .config import settings, Settings
from .exceptions import (
    APISpecRAGError,
    SpecParsingError,
    ChunkingError,
    EmbeddingError,
    VectorStoreError,
    RetrievalError,
    GenerationError,
    OllamaConnectionError,
    InsufficientInformationError,
)

__all__ = [
    # Models
    "OpenAPISpec",
    "PathItem",
    "Operation",
    "Parameter",
    "RequestBody",
    "Response",
    "Schema",
    "EndpointChunk",
    "ChunkMetadata",
    "QueryRequest",
    "RetrievalResult",
    "RetrievalResponse",
    "CurlCommand",
    "GenerationRequest",
    "GenerationResponse",
    "ValidationResult",
    "ValidationError",
    "ConfidenceScore",
    "PipelineRequest",
    "PipelineResponse",
    # Config
    "settings",
    "Settings",
    # Exceptions
    "APISpecRAGError",
    "SpecParsingError",
    "ChunkingError",
    "EmbeddingError",
    "VectorStoreError",
    "RetrievalError",
    "GenerationError",
    "OllamaConnectionError",
    "InsufficientInformationError",
]
