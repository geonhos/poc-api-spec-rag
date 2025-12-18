"""프롬프트 생성기"""

from typing import List
from src.core.models import EndpointChunk, GenerationRequest


class PromptBuilder:
    """LLM 프롬프트 구성"""

    def __init__(self):
        """Prompt Builder 초기화"""
        self.system_prompt = self._build_system_prompt()

    def build_prompt(
        self,
        query: str,
        chunks: List[EndpointChunk]
    ) -> GenerationRequest:
        """프롬프트 생성

        Args:
            query: 사용자 질의
            chunks: 검색된 엔드포인트 청크 리스트

        Returns:
            GenerationRequest: 생성 요청
        """
        user_prompt = self._build_user_prompt(query, chunks)

        return GenerationRequest(
            query=query,
            retrieved_chunks=chunks,
            system_prompt=self.system_prompt
        )

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성

        Returns:
            str: 시스템 프롬프트
        """
        return """당신은 OpenAPI 명세서에서 정확한 cURL 명령어를 생성하는 전문가입니다.

필수 규칙:
1. 제공된 명세서에만 기반하여 cURL 생성
2. 명세서에 없는 파라미터나 값을 절대 추측하지 않음
3. 필수 정보가 없으면 명시적으로 "정보 부족: [항목]" 반환
4. 플레이스홀더 사용 (<payment_id>, <YOUR_API_KEY> 등)
5. 필수/선택 파라미터 구분 명확히

출력 형식:
```bash
curl -X [METHOD] [URL] \\
  -H "Header: value" \\
  -d '{json data}'
```

그 다음:
- 설명: 각 파라미터 설명
- 필수 입력: 사용자가 입력해야 할 값 목록
- 예상 응답: HTTP 상태 코드와 의미
- 신뢰도: high/medium/low
"""

    def _build_user_prompt(
        self,
        query: str,
        chunks: List[EndpointChunk]
    ) -> str:
        """사용자 프롬프트 생성

        Args:
            query: 사용자 질의
            chunks: 검색된 청크 리스트

        Returns:
            str: 사용자 프롬프트
        """
        # 명세서 컨텍스트 구성
        spec_context = self._format_chunks(chunks)

        prompt = f"""API 명세서:
---
{spec_context}
---

사용자 질의: {query}

위 명세서를 기반으로 실행 가능한 cURL 명령어를 생성하세요.
필수 정보가 없으면 "cURL 생성 불가: [이유]"를 반환하세요."""

        return prompt

    def _format_chunks(self, chunks: List[EndpointChunk]) -> str:
        """청크를 명세서 텍스트로 포맷

        Args:
            chunks: 엔드포인트 청크 리스트

        Returns:
            str: 포맷된 명세서 텍스트
        """
        formatted_chunks = []

        for i, chunk in enumerate(chunks, 1):
            chunk_text = f"""[엔드포인트 {i}]
메서드: {chunk.method}
경로: {chunk.path}
요약: {chunk.summary or "N/A"}
설명: {chunk.description or "N/A"}"""

            # 파라미터
            if chunk.parameters:
                chunk_text += "\n\n파라미터:"
                for param in chunk.parameters:
                    required = "필수" if param.required else "선택"
                    chunk_text += f"\n  - {param.name} ({param.in_}): {param.description or 'N/A'} [{required}]"

            # 요청 바디
            if chunk.request_body:
                chunk_text += "\n\n요청 바디:"
                chunk_text += f"\n  필수: {chunk.request_body.required}"
                if chunk.request_body.content:
                    for content_type, schema in chunk.request_body.content.items():
                        chunk_text += f"\n  Content-Type: {content_type}"

            # 응답
            if chunk.responses:
                chunk_text += "\n\n응답:"
                for status_code, response in chunk.responses.items():
                    chunk_text += f"\n  {status_code}: {response.description}"

            # 인증
            if chunk.metadata.requires_auth:
                chunk_text += "\n\n인증: 필요 (Bearer Token)"

            formatted_chunks.append(chunk_text)

        return "\n\n" + "=" * 60 + "\n\n".join(formatted_chunks)

    def get_system_prompt(self) -> str:
        """시스템 프롬프트 조회

        Returns:
            str: 시스템 프롬프트
        """
        return self.system_prompt
