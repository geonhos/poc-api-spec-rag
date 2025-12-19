"""API 명세서 준수 검증 모듈"""

import re
from typing import List, Tuple, Dict

from src.core.models import EndpointChunk


class SpecValidator:
    """생성된 cURL 명령어가 API 명세서를 준수하는지 검증"""

    def __init__(self):
        """SpecValidator 초기화"""
        pass

    def validate(
        self, curl_components: Dict, endpoint_chunk: EndpointChunk
    ) -> Tuple[bool, List[str], float]:
        """
        cURL이 명세서를 준수하는지 검증

        Args:
            curl_components: CurlValidator.get_curl_components() 결과
            endpoint_chunk: 검색된 엔드포인트 청크

        Returns:
            Tuple[bool, List[str], float]: (유효 여부, 경고 메시지 리스트, 완성도 점수 0-1)
        """
        warnings = []
        completeness_score = 0.0

        # 1. HTTP 메서드 일치 확인
        method_match = self._validate_method(curl_components, endpoint_chunk)
        if not method_match:
            warnings.append(
                f"HTTP 메서드 불일치: cURL={curl_components['method']}, "
                f"명세={endpoint_chunk.metadata.method}"
            )
        else:
            completeness_score += 0.3

        # 2. 엔드포인트 경로 확인
        path_match = self._validate_path(curl_components, endpoint_chunk)
        if not path_match:
            warnings.append(
                f"엔드포인트 경로 불일치: URL에 '{endpoint_chunk.metadata.endpoint}'가 포함되지 않았습니다"
            )
        else:
            completeness_score += 0.2

        # 3. 인증 헤더 확인 (requires_auth인 경우)
        auth_valid = self._validate_auth(curl_components, endpoint_chunk)
        if not auth_valid:
            warnings.append("인증이 필요한 엔드포인트이지만 Authorization 헤더가 없습니다")
        else:
            completeness_score += 0.2

        # 4. Content-Type 헤더 확인 (request body가 있는 경우)
        content_type_valid = self._validate_content_type(curl_components, endpoint_chunk)
        if not content_type_valid:
            warnings.append("요청 바디가 있지만 Content-Type 헤더가 없습니다")
        else:
            completeness_score += 0.15

        # 5. 필수 파라미터 확인
        params_completeness = self._validate_required_params(curl_components, endpoint_chunk)
        completeness_score += params_completeness * 0.15

        is_valid = len(warnings) == 0
        return is_valid, warnings, completeness_score

    def _validate_method(self, curl_components: Dict, endpoint_chunk: EndpointChunk) -> bool:
        """HTTP 메서드 일치 확인"""
        curl_method = curl_components.get("method", "GET").upper()
        spec_method = endpoint_chunk.metadata.method.upper()
        return curl_method == spec_method

    def _validate_path(self, curl_components: Dict, endpoint_chunk: EndpointChunk) -> bool:
        """엔드포인트 경로 포함 확인"""
        url = curl_components.get("url", "")
        endpoint_path = endpoint_chunk.metadata.endpoint

        # 경로 파라미터 제거 (예: /payment/{id} → /payment/)
        normalized_path = re.sub(r"\{[^}]+\}", "", endpoint_path)

        # URL에 경로가 포함되어 있는지 확인
        return normalized_path in url or endpoint_path in url

    def _validate_auth(self, curl_components: Dict, endpoint_chunk: EndpointChunk) -> bool:
        """인증 헤더 확인"""
        if not endpoint_chunk.metadata.requires_auth:
            # 인증 불필요하면 통과
            return True

        headers = curl_components.get("headers", [])
        # Authorization 헤더가 있는지 확인
        for header in headers:
            if header.lower().startswith("authorization"):
                return True

        return False

    def _validate_content_type(self, curl_components: Dict, endpoint_chunk: EndpointChunk) -> bool:
        """Content-Type 헤더 확인"""
        body = curl_components.get("body")
        if not body:
            # Body가 없으면 Content-Type 불필요
            return True

        headers = curl_components.get("headers", [])
        # Content-Type 헤더가 있는지 확인
        for header in headers:
            if header.lower().startswith("content-type"):
                return True

        # Body가 있는데 Content-Type이 없으면 경고 (하지만 curl은 기본값 사용하므로 치명적이진 않음)
        return False

    def _validate_required_params(
        self, curl_components: Dict, endpoint_chunk: EndpointChunk
    ) -> float:
        """
        필수 파라미터 포함 여부 확인

        Returns:
            float: 필수 파라미터 완성도 점수 (0-1)
        """
        # 필수 파라미터 목록 추출
        required_params = []
        if endpoint_chunk.parameters:
            for param in endpoint_chunk.parameters:
                if param.required:
                    required_params.append(param.name)

        if not required_params:
            # 필수 파라미터가 없으면 완성도 100%
            return 1.0

        # cURL에서 파라미터 추출
        # - URL query params
        # - Path params
        # - Headers
        # - Body
        url = curl_components.get("url", "")
        headers = curl_components.get("headers", [])
        body = curl_components.get("body", "")

        # URL + headers + body를 합친 텍스트에서 파라미터 이름 검색
        combined_text = f"{url} {' '.join(headers)} {body}"

        found_count = 0
        for param_name in required_params:
            # 파라미터 이름 또는 플레이스홀더가 포함되어 있는지 확인
            # 예: payment_id, <PAYMENT_ID>, ${PAYMENT_ID}
            patterns = [
                param_name,
                f"<{param_name.upper()}>",
                f"${{{param_name.upper()}}}",
            ]
            for pattern in patterns:
                if pattern in combined_text:
                    found_count += 1
                    break

        # 완성도 = 발견된 필수 파라미터 수 / 전체 필수 파라미터 수
        completeness = found_count / len(required_params) if required_params else 1.0
        return completeness
