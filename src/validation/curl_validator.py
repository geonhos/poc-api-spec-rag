"""cURL 명령어 문법 검증 모듈"""

import re
from typing import List, Tuple

from src.core.exceptions import ValidationError


class CurlValidator:
    """cURL 명령어의 문법적 유효성을 검증"""

    # 지원되는 HTTP 메서드
    VALID_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}

    def __init__(self):
        """CurlValidator 초기화"""
        pass

    def validate(self, curl_command: str) -> Tuple[bool, List[str]]:
        """
        cURL 명령어 문법 검증

        Args:
            curl_command: 검증할 cURL 명령어

        Returns:
            Tuple[bool, List[str]]: (유효 여부, 오류 메시지 리스트)
        """
        errors = []

        # 1. curl 명령어로 시작하는지 확인
        if not self._starts_with_curl(curl_command):
            errors.append("명령어가 'curl'로 시작하지 않습니다")
            return False, errors

        # 2. HTTP 메서드 검증
        method_valid, method_errors = self._validate_method(curl_command)
        errors.extend(method_errors)

        # 3. URL 존재 확인
        url_valid, url_errors = self._validate_url(curl_command)
        errors.extend(url_errors)

        # 4. Headers 형식 검증
        headers_valid, header_errors = self._validate_headers(curl_command)
        errors.extend(header_errors)

        # 5. Request body 형식 검증
        body_valid, body_errors = self._validate_body(curl_command)
        errors.extend(body_errors)

        is_valid = len(errors) == 0
        return is_valid, errors

    def _starts_with_curl(self, command: str) -> bool:
        """curl로 시작하는지 확인"""
        stripped = command.strip()
        return stripped.startswith("curl ")

    def _validate_method(self, command: str) -> Tuple[bool, List[str]]:
        """HTTP 메서드 검증"""
        errors = []

        # -X 또는 --request 옵션 찾기
        method_pattern = r"-X\s+(\w+)|--request\s+(\w+)"
        matches = re.findall(method_pattern, command)

        if not matches:
            # 메서드가 명시되지 않았으면 기본값 GET (valid)
            return True, []

        # 모든 매치에서 메서드 추출
        for match in matches:
            method = match[0] or match[1]
            if method.upper() not in self.VALID_METHODS:
                errors.append(f"지원되지 않는 HTTP 메서드: {method}")

        return len(errors) == 0, errors

    def _validate_url(self, command: str) -> Tuple[bool, List[str]]:
        """URL 존재 확인"""
        errors = []

        # URL 패턴: http(s)://... 또는 플레이스홀더
        url_patterns = [
            r"https?://\S+",  # 실제 URL
            r"<[A-Z_]+>",  # 플레이스홀더 (예: <BASE_URL>)
            r"\$\{[A-Z_]+\}",  # 환경변수 (예: ${BASE_URL})
        ]

        found_url = False
        for pattern in url_patterns:
            if re.search(pattern, command):
                found_url = True
                break

        if not found_url:
            errors.append("URL이 명시되지 않았습니다")

        return found_url, errors

    def _validate_headers(self, command: str) -> Tuple[bool, List[str]]:
        """Headers 형식 검증"""
        errors = []

        # -H 또는 --header 옵션 찾기
        header_pattern = r'-H\s+"([^"]+)"|--header\s+"([^"]+)"'
        matches = re.findall(header_pattern, command)

        for match in matches:
            header = match[0] or match[1]
            # Header는 "Key: Value" 형식이어야 함
            if ":" not in header:
                errors.append(f"잘못된 헤더 형식: {header} (Key: Value 형식이어야 합니다)")

        return len(errors) == 0, errors

    def _validate_body(self, command: str) -> Tuple[bool, List[str]]:
        """Request body 형식 검증"""
        errors = []

        # -d, --data, --data-raw 옵션 찾기
        body_pattern = r'-d\s+"([^"]+)"|--data\s+"([^"]+)"|--data-raw\s+"([^"]+)"'
        matches = re.findall(body_pattern, command)

        # Body가 있으면 기본적으로 유효 (JSON 파싱은 하지 않음)
        # 플레이스홀더나 실제 데이터 모두 허용

        return True, errors

    def get_curl_components(self, curl_command: str) -> dict:
        """
        cURL 명령어를 구성 요소로 분해

        Args:
            curl_command: cURL 명령어

        Returns:
            dict: method, url, headers, body 등의 구성 요소
        """
        components = {
            "method": None,
            "url": None,
            "headers": [],
            "body": None,
        }

        # Method 추출
        method_pattern = r"-X\s+(\w+)|--request\s+(\w+)"
        method_match = re.search(method_pattern, curl_command)
        if method_match:
            components["method"] = (method_match.group(1) or method_match.group(2)).upper()
        else:
            components["method"] = "GET"  # 기본값

        # URL 추출
        url_patterns = [
            r"(https?://\S+)",
            r"(<[A-Z_]+>(?:/\S*)?)",
            r"(\$\{[A-Z_]+\}(?:/\S*)?)",
        ]
        for pattern in url_patterns:
            url_match = re.search(pattern, curl_command)
            if url_match:
                components["url"] = url_match.group(1)
                break

        # Headers 추출
        header_pattern = r'-H\s+"([^"]+)"|--header\s+"([^"]+)"'
        header_matches = re.findall(header_pattern, curl_command)
        components["headers"] = [match[0] or match[1] for match in header_matches]

        # Body 추출
        body_pattern = r'-d\s+"([^"]+)"|--data\s+"([^"]+)"|--data-raw\s+"([^"]+)"'
        body_match = re.search(body_pattern, curl_command)
        if body_match:
            components["body"] = body_match.group(1) or body_match.group(2) or body_match.group(3)

        return components
