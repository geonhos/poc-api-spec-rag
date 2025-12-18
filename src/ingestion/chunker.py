"""엔드포인트 청킹"""

from typing import List
from src.core.models import OpenAPISpec, EndpointChunk, ChunkMetadata, Operation
from src.core.exceptions import ChunkingError


class EndpointChunker:
    """엔드포인트 중심 청킹"""

    def chunk_spec(self, spec: OpenAPISpec) -> List[EndpointChunk]:
        """OpenAPI 명세서를 엔드포인트 단위로 청킹

        Args:
            spec: OpenAPI 명세서

        Returns:
            List[EndpointChunk]: 청크 리스트

        Raises:
            ChunkingError: 청킹 실패 시
        """
        chunks = []

        try:
            for path, path_item in spec.paths.items():
                # 각 HTTP 메서드별로 청크 생성
                methods = {
                    "get": path_item.get,
                    "post": path_item.post,
                    "put": path_item.put,
                    "delete": path_item.delete,
                    "patch": path_item.patch,
                    "options": path_item.options,
                    "head": path_item.head,
                }

                for method, operation in methods.items():
                    if operation is not None:
                        chunk = self._create_chunk(
                            path=path,
                            method=method.upper(),
                            operation=operation
                        )
                        chunks.append(chunk)

            if not chunks:
                raise ChunkingError("No chunks created from spec")

            return chunks

        except Exception as e:
            raise ChunkingError(f"Failed to chunk spec: {e}")

    def _create_chunk(
        self,
        path: str,
        method: str,
        operation: Operation
    ) -> EndpointChunk:
        """단일 엔드포인트 청크 생성

        Args:
            path: API 경로
            method: HTTP 메서드
            operation: Operation 객체

        Returns:
            EndpointChunk: 생성된 청크
        """
        # 청크 ID 생성
        chunk_id = f"{method}_{path}"

        # 메타데이터 생성
        metadata = ChunkMetadata(
            endpoint=path,
            method=method,
            tags=operation.tags or [],
            operation_id=operation.operationId,
            requires_auth=self._requires_auth(operation),
            content_type=self._get_content_type(operation)
        )

        # 청크 생성
        chunk = EndpointChunk(
            chunk_id=chunk_id,
            method=method,
            path=path,
            summary=operation.summary,
            description=operation.description,
            parameters=operation.parameters or [],
            request_body=operation.requestBody,
            responses=operation.responses,
            metadata=metadata
        )

        return chunk

    def _requires_auth(self, operation: Operation) -> bool:
        """인증 필요 여부 확인

        Args:
            operation: Operation 객체

        Returns:
            bool: 인증이 필요하면 True
        """
        if operation.security:
            return len(operation.security) > 0
        return False

    def _get_content_type(self, operation: Operation) -> str:
        """Content-Type 추출

        Args:
            operation: Operation 객체

        Returns:
            str: Content-Type (기본값: application/json)
        """
        if operation.requestBody and operation.requestBody.content:
            content_types = list(operation.requestBody.content.keys())
            if content_types:
                return content_types[0]

        return "application/json"
