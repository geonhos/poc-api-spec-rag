"""신뢰도 점수 계산 모듈"""

from typing import List

from src.core.models import ConfidenceScore


class ConfidenceScorer:
    """cURL 생성 신뢰도 점수 계산"""

    def __init__(self):
        """ConfidenceScorer 초기화"""
        pass

    def calculate_score(
        self,
        similarity: float,
        spec_completeness: float,
        syntax_valid: bool,
        spec_valid: bool,
    ) -> ConfidenceScore:
        """
        신뢰도 점수 계산

        Args:
            similarity: 벡터 검색 유사도 (0-1)
            spec_completeness: 명세 완성도 점수 (0-1)
            syntax_valid: cURL 문법 유효성
            spec_valid: 명세 준수 여부

        Returns:
            ConfidenceScore: 계산된 신뢰도 점수 및 레벨
        """
        # 검증 통과 여부 (문법 + 명세 준수)
        validation_passed = syntax_valid and spec_valid

        # ConfidenceScore.calculate() 클래스 메서드 사용
        return ConfidenceScore.calculate(
            similarity=similarity,
            spec_completeness=spec_completeness,
            validation_passed=validation_passed,
        )

    def get_confidence_explanation(self, confidence: ConfidenceScore) -> str:
        """
        신뢰도 점수 설명 생성

        Args:
            confidence: ConfidenceScore 객체

        Returns:
            str: 사람이 읽을 수 있는 설명
        """
        explanation = f"신뢰도: {confidence.level} ({confidence.overall:.2f})\n"
        explanation += f"- 검색 유사도: {confidence.similarity:.2f}\n"
        explanation += f"- 명세 완성도: {confidence.spec_completeness:.2f}\n"
        explanation += f"- 검증 통과: {'예' if confidence.validation_passed else '아니오'}"
        return explanation
