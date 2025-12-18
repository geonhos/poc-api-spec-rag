"""OpenAPI 명세서 파서"""

import yaml
import json
from pathlib import Path
from typing import Union, Dict, Any

from src.core.models import OpenAPISpec
from src.core.exceptions import SpecParsingError


class OpenAPIParser:
    """OpenAPI 명세서 파서 (YAML/JSON)"""

    def parse_file(self, file_path: Union[str, Path]) -> OpenAPISpec:
        """파일에서 OpenAPI 명세서 파싱

        Args:
            file_path: OpenAPI 명세서 파일 경로 (.yaml, .yml, .json)

        Returns:
            OpenAPISpec: 파싱된 명세서

        Raises:
            SpecParsingError: 파싱 실패 시
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise SpecParsingError(f"File not found: {file_path}")

        try:
            content = file_path.read_text(encoding="utf-8")
            return self.parse_string(content, file_path.suffix)
        except Exception as e:
            raise SpecParsingError(f"Failed to read file {file_path}: {e}")

    def parse_string(self, content: str, format: str = ".yaml") -> OpenAPISpec:
        """문자열에서 OpenAPI 명세서 파싱

        Args:
            content: OpenAPI 명세서 문자열
            format: 파일 형식 (".yaml", ".yml", ".json")

        Returns:
            OpenAPISpec: 파싱된 명세서

        Raises:
            SpecParsingError: 파싱 실패 시
        """
        try:
            if format in [".yaml", ".yml"]:
                data = yaml.safe_load(content)
            elif format == ".json":
                data = json.loads(content)
            else:
                raise SpecParsingError(f"Unsupported format: {format}")

            return self.parse_dict(data)
        except yaml.YAMLError as e:
            raise SpecParsingError(f"YAML parsing error: {e}")
        except json.JSONDecodeError as e:
            raise SpecParsingError(f"JSON parsing error: {e}")
        except Exception as e:
            raise SpecParsingError(f"Parsing error: {e}")

    def parse_dict(self, data: Dict[str, Any]) -> OpenAPISpec:
        """딕셔너리에서 OpenAPI 명세서 파싱

        Args:
            data: OpenAPI 명세서 딕셔너리

        Returns:
            OpenAPISpec: 파싱된 명세서

        Raises:
            SpecParsingError: 파싱 실패 시
        """
        try:
            # OpenAPI 버전 확인
            openapi_version = data.get("openapi")
            if not openapi_version:
                raise SpecParsingError("Missing 'openapi' field")

            if not openapi_version.startswith("3."):
                raise SpecParsingError(
                    f"Unsupported OpenAPI version: {openapi_version}. "
                    "Only OpenAPI 3.x is supported."
                )

            # Pydantic 모델로 검증 및 파싱
            spec = OpenAPISpec(**data)
            return spec

        except Exception as e:
            raise SpecParsingError(f"Failed to parse OpenAPI spec: {e}")

    def validate_spec(self, spec: OpenAPISpec) -> bool:
        """명세서 유효성 검증

        Args:
            spec: OpenAPI 명세서

        Returns:
            bool: 유효하면 True

        Raises:
            SpecParsingError: 검증 실패 시
        """
        # 기본 필드 확인
        if not spec.paths:
            raise SpecParsingError("No paths defined in OpenAPI spec")

        # 각 경로에 최소 하나의 operation이 있는지 확인
        valid_operations = 0
        for path, path_item in spec.paths.items():
            operations = [
                op for op in [
                    path_item.get, path_item.post, path_item.put,
                    path_item.delete, path_item.patch, path_item.options,
                    path_item.head
                ] if op is not None
            ]

            if operations:
                valid_operations += len(operations)

        if valid_operations == 0:
            raise SpecParsingError("No valid operations found in OpenAPI spec")

        return True
