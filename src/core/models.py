"""Pydantic 모델 정의"""

from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field


# ============================================================================
# OpenAPI Specification Models
# ============================================================================

class Schema(BaseModel):
    """OpenAPI Schema 객체"""
    type: Optional[str] = None
    format: Optional[str] = None
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    items: Optional[Dict[str, Any]] = None
    required: Optional[List[str]] = None
    enum: Optional[List[Any]] = None
    example: Optional[Any] = None
    ref: Optional[str] = Field(None, alias="$ref")


class Parameter(BaseModel):
    """OpenAPI Parameter 객체"""
    name: str
    in_: Literal["query", "header", "path", "cookie"] = Field(..., alias="in")
    description: Optional[str] = None
    required: Optional[bool] = False
    schema_: Optional[Schema] = Field(None, alias="schema")
    example: Optional[Any] = None


class RequestBody(BaseModel):
    """OpenAPI RequestBody 객체"""
    description: Optional[str] = None
    content: Dict[str, Any]  # media type -> schema
    required: Optional[bool] = False


class Response(BaseModel):
    """OpenAPI Response 객체"""
    description: str
    content: Optional[Dict[str, Any]] = None  # media type -> schema


class Operation(BaseModel):
    """OpenAPI Operation 객체 (GET, POST 등)"""
    summary: Optional[str] = None
    description: Optional[str] = None
    operationId: Optional[str] = None
    tags: Optional[List[str]] = None
    parameters: Optional[List[Parameter]] = None
    requestBody: Optional[RequestBody] = None
    responses: Dict[str, Response]
    security: Optional[List[Dict[str, List[str]]]] = None


class PathItem(BaseModel):
    """OpenAPI Path Item (경로별 엔드포인트)"""
    get: Optional[Operation] = None
    post: Optional[Operation] = None
    put: Optional[Operation] = None
    delete: Optional[Operation] = None
    patch: Optional[Operation] = None
    options: Optional[Operation] = None
    head: Optional[Operation] = None


class OpenAPISpec(BaseModel):
    """OpenAPI Specification (전체 구조)"""
    openapi: str  # "3.0.0", "3.1.0"
    info: Dict[str, Any]
    servers: Optional[List[Dict[str, Any]]] = None
    paths: Dict[str, PathItem]
    components: Optional[Dict[str, Any]] = None


# ============================================================================
# RAG Chunking Models
# ============================================================================

class ChunkMetadata(BaseModel):
    """청크 메타데이터"""
    endpoint: str  # "/api/v1/payment/approve"
    method: str  # "POST", "GET", etc.
    tags: List[str] = Field(default_factory=list)
    operation_id: Optional[str] = None
    requires_auth: bool = False
    content_type: Optional[str] = None


class EndpointChunk(BaseModel):
    """엔드포인트 청크 (벡터 저장 단위)"""
    chunk_id: str  # "POST_/api/v1/payment/approve"
    method: str
    path: str
    summary: Optional[str] = None
    description: Optional[str] = None
    parameters: List[Parameter] = Field(default_factory=list)
    request_body: Optional[RequestBody] = None
    responses: Dict[str, Response]
    metadata: ChunkMetadata

    def to_embedding_text(self) -> str:
        """임베딩용 텍스트 생성"""
        parts = [
            f"{self.method} {self.path}",
        ]

        if self.summary:
            parts.append(f"- {self.summary}")

        if self.description:
            parts.append(f"Description: {self.description}")

        if self.parameters:
            param_names = [p.name for p in self.parameters]
            parts.append(f"Parameters: {', '.join(param_names)}")

        if self.metadata.tags:
            parts.append(f"Tags: {', '.join(self.metadata.tags)}")

        return "\n".join(parts)


# ============================================================================
# Query & Retrieval Models
# ============================================================================

class QueryRequest(BaseModel):
    """사용자 질의"""
    query: str
    filters: Optional[Dict[str, Any]] = None  # 메타데이터 필터
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievalResult(BaseModel):
    """검색 결과"""
    chunk: EndpointChunk
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    rank: int  # 1-based ranking


class RetrievalResponse(BaseModel):
    """검색 응답"""
    results: List[RetrievalResult]
    query: str
    total_results: int


# ============================================================================
# Generation Models
# ============================================================================

class CurlCommand(BaseModel):
    """생성된 cURL 명령어"""
    command: str
    explanation: str
    required_params: List[str] = Field(default_factory=list)
    optional_params: List[str] = Field(default_factory=list)
    expected_responses: Dict[str, str]  # status code -> description


class GenerationRequest(BaseModel):
    """cURL 생성 요청"""
    query: str
    retrieved_chunks: List[EndpointChunk]
    system_prompt: Optional[str] = None


class GenerationResponse(BaseModel):
    """cURL 생성 응답"""
    curl_command: CurlCommand
    source_endpoint: str  # 사용된 엔드포인트
    confidence: Literal["high", "medium", "low"]
    warnings: List[str] = Field(default_factory=list)


# ============================================================================
# Validation Models
# ============================================================================

class ValidationError(BaseModel):
    """검증 오류"""
    field: str
    message: str
    severity: Literal["error", "warning"]


class ValidationResult(BaseModel):
    """검증 결과"""
    valid: bool
    errors: List[ValidationError] = Field(default_factory=list)
    warnings: List[ValidationError] = Field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """에러가 있는지 확인"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """경고가 있는지 확인"""
        return len(self.warnings) > 0


class ConfidenceScore(BaseModel):
    """신뢰도 점수"""
    similarity: float = Field(..., ge=0.0, le=1.0)
    spec_completeness: float = Field(..., ge=0.0, le=1.0)
    validation_passed: bool
    overall: float = Field(..., ge=0.0, le=1.0)
    level: Literal["high", "medium", "low"]

    @classmethod
    def calculate(
        cls,
        similarity: float,
        spec_completeness: float,
        validation_passed: bool
    ) -> "ConfidenceScore":
        """신뢰도 점수 계산"""
        overall = (
            similarity * 0.4 +
            spec_completeness * 0.3 +
            (1.0 if validation_passed else 0.0) * 0.3
        )

        if overall > 0.8:
            level = "high"
        elif overall > 0.6:
            level = "medium"
        else:
            level = "low"

        return cls(
            similarity=similarity,
            spec_completeness=spec_completeness,
            validation_passed=validation_passed,
            overall=overall,
            level=level
        )


# ============================================================================
# Complete Pipeline Models
# ============================================================================

class PipelineRequest(BaseModel):
    """전체 파이프라인 요청"""
    query: str
    spec_file: Optional[str] = None  # OpenAPI spec 파일 경로
    top_k: int = Field(default=5, ge=1, le=20)


class PipelineResponse(BaseModel):
    """전체 파이프라인 응답"""
    success: bool
    curl_command: Optional[CurlCommand] = None
    confidence: Optional[ConfidenceScore] = None
    validation: Optional[ValidationResult] = None
    error_message: Optional[str] = None
    retrieved_endpoints: List[str] = Field(default_factory=list)
