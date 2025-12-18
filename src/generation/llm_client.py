"""Ollama LLM 클라이언트"""

import ollama
from typing import Optional

from src.core.config import settings
from src.core.exceptions import GenerationError, OllamaConnectionError


class OllamaLLMClient:
    """Ollama를 사용한 LLM 클라이언트"""

    def __init__(self, model: str = None):
        """
        Args:
            model: LLM 모델 이름 (기본값: settings.OLLAMA_LLM_MODEL)
        """
        self.model = model or settings.OLLAMA_LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> str:
        """텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트

        Returns:
            str: 생성된 텍스트

        Raises:
            GenerationError: 생성 실패 시
            OllamaConnectionError: Ollama 연결 실패 시
        """
        try:
            # 메시지 구성
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Ollama 호출
            response = ollama.chat(
                model=self.model,
                messages=messages,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            )

            # 응답 추출
            if not response or "message" not in response:
                raise GenerationError("No response from Ollama")

            generated_text = response["message"]["content"]

            if not generated_text:
                raise GenerationError("Empty response from Ollama")

            return generated_text

        except ConnectionError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama: {e}. "
                "Make sure Ollama is running (ollama serve)"
            )
        except Exception as e:
            raise GenerationError(f"Failed to generate text: {e}")

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ):
        """스트리밍 텍스트 생성

        Args:
            prompt: 사용자 프롬프트
            system_prompt: 시스템 프롬프트

        Yields:
            str: 생성된 텍스트 청크

        Raises:
            GenerationError: 생성 실패 시
            OllamaConnectionError: Ollama 연결 실패 시
        """
        try:
            # 메시지 구성
            messages = []

            if system_prompt:
                messages.append({
                    "role": "system",
                    "content": system_prompt
                })

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Ollama 스트리밍 호출
            stream = ollama.chat(
                model=self.model,
                messages=messages,
                stream=True,
                options={
                    "temperature": self.temperature,
                    "num_predict": self.max_tokens,
                }
            )

            for chunk in stream:
                if "message" in chunk and "content" in chunk["message"]:
                    yield chunk["message"]["content"]

        except ConnectionError as e:
            raise OllamaConnectionError(
                f"Failed to connect to Ollama: {e}. "
                "Make sure Ollama is running (ollama serve)"
            )
        except Exception as e:
            raise GenerationError(f"Failed to generate stream: {e}")
