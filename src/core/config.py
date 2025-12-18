"""프로젝트 설정 관리"""

import os
from pathlib import Path
from typing import Optional
from pydantic import ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    """애플리케이션 설정"""

    # 프로젝트 경로
    PROJECT_ROOT: Path = Path(__file__).parent.parent.parent
    DATA_DIR: Path = PROJECT_ROOT / "data"
    SPECS_DIR: Path = DATA_DIR / "specs"
    CHROMA_DB_DIR: Path = DATA_DIR / "chroma_db"
    CACHE_DIR: Path = DATA_DIR / "cache"

    # Ollama 설정
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"
    OLLAMA_LLM_MODEL: str = "gpt-oss:20b"
    OLLAMA_TIMEOUT: int = 120  # seconds

    # ChromaDB 설정
    CHROMA_COLLECTION_NAME: str = "api_spec_endpoints"
    CHROMA_DISTANCE_METRIC: str = "cosine"

    # RAG 설정
    TOP_K: int = 5  # 검색할 청크 개수
    SIMILARITY_THRESHOLD: float = 0.5  # 최소 유사도 임계값
    HIGH_CONFIDENCE_THRESHOLD: float = 0.7  # 고신뢰도 임계값

    # LLM 생성 설정
    LLM_TEMPERATURE: float = 0.1  # 낮을수록 deterministic
    LLM_MAX_TOKENS: int = 2000

    # 로깅
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def ensure_directories(self):
        """필요한 디렉토리 생성"""
        for dir_path in [
            self.DATA_DIR,
            self.SPECS_DIR,
            self.CHROMA_DB_DIR,
            self.CACHE_DIR,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


# 전역 설정 인스턴스
settings = Settings()

# 디렉토리 생성
settings.ensure_directories()
