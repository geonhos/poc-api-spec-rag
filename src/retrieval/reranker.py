"""LLM 기반 검색 결과 재정렬"""

import re
import ollama
from typing import List

from src.core.config import settings
from src.core.models import RetrievalResult
from src.core.exceptions import GenerationError, OllamaConnectionError


class LLMReranker:
    """LLM을 사용한 검색 결과 재정렬

    벡터 검색으로 가져온 Top-K 결과를 LLM이 의미적 관련성을 평가하여 재정렬합니다.
    이를 통해 한국어 질의와 API 엔드포인트 간의 정확한 매칭을 달성합니다.
    """

    def __init__(self, model: str = None):
        """
        Args:
            model: LLM 모델 이름 (기본값: settings.OLLAMA_LLM_MODEL)
        """
        self.model = model or settings.OLLAMA_LLM_MODEL

    def rerank(
        self,
        query: str,
        results: List[RetrievalResult],
        top_n: int = 3
    ) -> List[RetrievalResult]:
        """검색 결과를 LLM으로 재정렬

        Args:
            query: 사용자 질의
            results: 벡터 검색 결과 리스트
            top_n: 반환할 상위 결과 개수

        Returns:
            List[RetrievalResult]: 재정렬된 결과 (상위 top_n개)

        Raises:
            GenerationError: 재정렬 실패 시
            OllamaConnectionError: Ollama 연결 실패 시
        """
        if not results:
            return []

        if len(results) == 1:
            return results

        try:
            # LLM 프롬프트 생성
            prompt = self._build_rerank_prompt(query, results)

            # LLM 호출
            response = ollama.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": self._get_system_prompt()
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                options={
                    "temperature": 0.3,  # 약간의 창의성
                    "num_predict": 200,
                }
            )

            # 응답에서 순위 추출
            llm_output = response["message"]["content"]
            ranking = self._parse_ranking(llm_output, len(results))

            # 결과 재정렬
            reranked = self._apply_ranking(results, ranking)

            return reranked[:top_n]

        except ConnectionError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama: {e}"
            )
        except Exception as e:
            # Reranking 실패 시 원래 순서 반환
            print(f"Warning: Reranking failed ({e}), using original order")
            return results[:top_n]

    def _get_system_prompt(self) -> str:
        """시스템 프롬프트 생성

        Returns:
            str: 시스템 프롬프트
        """
        return """당신은 API 엔드포인트 매칭 전문가입니다.

사용자 질의와 API 엔드포인트 목록이 주어지면, 가장 관련있는 엔드포인트를 찾습니다.

매칭 규칙:
- "승인" → approve, POST
- "취소" → cancel, DELETE
- "조회" → status/get, GET
- "생성/등록" → create, POST
- "수정/변경" → update, PUT
- "삭제/제거" → delete, DELETE

출력 형식:
가장 관련있는 번호: N
이유: [간단한 설명]"""

    def _build_rerank_prompt(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> str:
        """재정렬 프롬프트 생성

        Args:
            query: 사용자 질의
            results: 검색 결과

        Returns:
            str: 프롬프트
        """
        # 엔드포인트 목록 생성
        endpoints = []
        for i, result in enumerate(results, 1):
            chunk = result.chunk
            endpoint_desc = f"{i}. {chunk.method} {chunk.path}"
            if chunk.summary:
                endpoint_desc += f" - {chunk.summary}"
            if chunk.description:
                endpoint_desc += f"\n   설명: {chunk.description[:100]}"
            endpoints.append(endpoint_desc)

        endpoints_text = "\n".join(endpoints)

        prompt = f"""사용자 질의: "{query}"

API 엔드포인트 목록:
{endpoints_text}

위 질의와 가장 관련있는 엔드포인트를 선택하세요."""

        return prompt

    def _parse_ranking(self, llm_output: str, num_results: int) -> List[int]:
        """LLM 출력에서 순위 파싱

        Args:
            llm_output: LLM 응답 텍스트
            num_results: 결과 개수

        Returns:
            List[int]: 순위 리스트 (1-indexed)
        """
        # "가장 관련있는 번호: N" 형식 파싱
        match = re.search(r'가장 관련있는 번호:\s*(\d+)', llm_output)
        if match:
            top_choice = int(match.group(1))
            if 1 <= top_choice <= num_results:
                # 선택된 번호를 1위로, 나머지는 원래 순서
                ranking = [top_choice]
                for i in range(1, num_results + 1):
                    if i != top_choice:
                        ranking.append(i)
                return ranking

        # 대체: 첫 번째 숫자 찾기
        numbers = re.findall(r'\d+', llm_output)
        if numbers:
            top_choice = int(numbers[0])
            if 1 <= top_choice <= num_results:
                ranking = [top_choice]
                for i in range(1, num_results + 1):
                    if i != top_choice:
                        ranking.append(i)
                return ranking

        # 파싱 실패 시 원래 순서
        return list(range(1, num_results + 1))

    def _apply_ranking(
        self,
        results: List[RetrievalResult],
        ranking: List[int]
    ) -> List[RetrievalResult]:
        """순위를 결과에 적용

        Args:
            results: 원본 결과
            ranking: 순위 리스트 (1-indexed)

        Returns:
            List[RetrievalResult]: 재정렬된 결과
        """
        reranked = []
        for rank_position, original_position in enumerate(ranking, 1):
            if original_position <= len(results):
                result = results[original_position - 1]
                # rank 업데이트
                result.rank = rank_position
                reranked.append(result)

        return reranked
