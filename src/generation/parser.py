"""LLM 출력 파서"""

import re
from typing import Dict, List, Literal
from src.core.models import CurlCommand, GenerationResponse
from src.core.exceptions import GenerationError


class OutputParser:
    """LLM 출력 파싱"""

    def parse_curl_response(
        self,
        llm_output: str,
        source_endpoint: str
    ) -> GenerationResponse:
        """LLM 출력을 GenerationResponse로 파싱

        Args:
            llm_output: LLM 생성 텍스트
            source_endpoint: 사용된 엔드포인트

        Returns:
            GenerationResponse: 파싱된 응답

        Raises:
            GenerationError: 파싱 실패 시
        """
        try:
            # cURL 생성 불가 체크
            if self._is_insufficient_info(llm_output):
                missing_info = self._extract_missing_info(llm_output)
                return GenerationResponse(
                    curl_command=CurlCommand(
                        command="",
                        explanation=llm_output,
                        required_params=[],
                        optional_params=[],
                        expected_responses={}
                    ),
                    source_endpoint=source_endpoint,
                    confidence="low",
                    warnings=[f"정보 부족: {missing_info}"]
                )

            # cURL 명령어 추출
            curl_command = self._extract_curl_command(llm_output)

            # 설명 추출
            explanation = self._extract_explanation(llm_output)

            # 필수/선택 파라미터 추출
            required_params = self._extract_required_params(llm_output)
            optional_params = self._extract_optional_params(llm_output)

            # 예상 응답 추출
            expected_responses = self._extract_expected_responses(llm_output)

            # 신뢰도 추출
            confidence = self._extract_confidence(llm_output)

            # 경고 추출
            warnings = self._extract_warnings(llm_output)

            return GenerationResponse(
                curl_command=CurlCommand(
                    command=curl_command,
                    explanation=explanation,
                    required_params=required_params,
                    optional_params=optional_params,
                    expected_responses=expected_responses
                ),
                source_endpoint=source_endpoint,
                confidence=confidence,
                warnings=warnings
            )

        except Exception as e:
            raise GenerationError(f"Failed to parse LLM output: {e}")

    def _is_insufficient_info(self, text: str) -> bool:
        """정보 부족 여부 확인

        Args:
            text: LLM 출력

        Returns:
            bool: 정보가 부족하면 True
        """
        patterns = [
            r"cURL 생성 불가",
            r"정보 부족",
            r"insufficient information",
            r"cannot generate",
        ]

        return any(re.search(pattern, text, re.IGNORECASE) for pattern in patterns)

    def _extract_missing_info(self, text: str) -> str:
        """부족한 정보 추출

        Args:
            text: LLM 출력

        Returns:
            str: 부족한 정보
        """
        match = re.search(r"정보 부족:\s*(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        match = re.search(r"cURL 생성 불가:\s*(.+)", text, re.IGNORECASE)
        if match:
            return match.group(1).strip()

        return "알 수 없음"

    def _extract_curl_command(self, text: str) -> str:
        """cURL 명령어 추출

        Args:
            text: LLM 출력

        Returns:
            str: cURL 명령어

        Raises:
            GenerationError: cURL 명령어를 찾을 수 없을 때
        """
        # 코드 블록에서 추출
        match = re.search(r"```(?:bash|sh)?\s*\n(curl\s+.+?)\n```", text, re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1).strip()

        # 단순 curl로 시작하는 라인 찾기
        lines = text.split("\n")
        curl_lines = []
        in_curl = False

        for line in lines:
            if line.strip().startswith("curl"):
                in_curl = True
                curl_lines.append(line)
            elif in_curl:
                if line.strip().endswith("\\"):
                    curl_lines.append(line)
                elif line.strip() and not line.strip().startswith(("-", "}")):
                    curl_lines.append(line)
                    break
                elif not line.strip():
                    break

        if curl_lines:
            return "\n".join(curl_lines).strip()

        raise GenerationError("Could not extract cURL command from output")

    def _extract_explanation(self, text: str) -> str:
        """설명 추출

        Args:
            text: LLM 출력

        Returns:
            str: 설명
        """
        # "설명:" 이후 텍스트
        match = re.search(r"설명:\s*\n(.+?)(?:\n\n|필수 입력|예상 응답|$)", text, re.DOTALL)
        if match:
            return match.group(1).strip()

        return ""

    def _extract_required_params(self, text: str) -> List[str]:
        """필수 파라미터 추출

        Args:
            text: LLM 출력

        Returns:
            List[str]: 필수 파라미터 목록
        """
        params = []

        # "필수 입력:" 섹션 찾기
        match = re.search(r"필수 입력:\s*\n(.+?)(?:\n\n|예상 응답|신뢰도|$)", text, re.DOTALL)
        if match:
            lines = match.group(1).strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-"):
                    param = line[1:].strip()
                    params.append(param)

        return params

    def _extract_optional_params(self, text: str) -> List[str]:
        """선택 파라미터 추출

        Args:
            text: LLM 출력

        Returns:
            List[str]: 선택 파라미터 목록
        """
        # 현재는 빈 리스트 반환 (필요시 구현)
        return []

    def _extract_expected_responses(self, text: str) -> Dict[str, str]:
        """예상 응답 추출

        Args:
            text: LLM 출력

        Returns:
            Dict[str, str]: 상태 코드 -> 설명 매핑
        """
        responses = {}

        # "예상 응답:" 섹션 찾기
        match = re.search(r"예상 응답:\s*\n(.+?)(?:\n\n|신뢰도|$)", text, re.DOTALL)
        if match:
            lines = match.group(1).strip().split("\n")
            for line in lines:
                line = line.strip()
                if line.startswith("-"):
                    line = line[1:].strip()

                # "200: 성공" 형식
                status_match = re.match(r"(\d{3}):\s*(.+)", line)
                if status_match:
                    code = status_match.group(1)
                    desc = status_match.group(2).strip()
                    responses[code] = desc

        return responses

    def _extract_confidence(self, text: str) -> Literal["high", "medium", "low"]:
        """신뢰도 추출

        Args:
            text: LLM 출력

        Returns:
            Literal["high", "medium", "low"]: 신뢰도
        """
        text_lower = text.lower()

        if "신뢰도: high" in text_lower or "신뢰도: 높음" in text_lower:
            return "high"
        elif "신뢰도: medium" in text_lower or "신뢰도: 중간" in text_lower:
            return "medium"
        elif "신뢰도: low" in text_lower or "신뢰도: 낮음" in text_lower:
            return "low"

        # 기본값: medium
        return "medium"

    def _extract_warnings(self, text: str) -> List[str]:
        """경고 추출

        Args:
            text: LLM 출력

        Returns:
            List[str]: 경고 목록
        """
        warnings = []

        # "⚠️" 또는 "경고" 포함 라인 찾기
        lines = text.split("\n")
        for line in lines:
            if "⚠️" in line or "경고" in line.lower():
                warnings.append(line.strip())

        return warnings
