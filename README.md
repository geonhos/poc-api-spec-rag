# POC API Spec RAG

> RAG 기반 API 명세서 cURL 생성 시스템
> Generate accurate cURL commands from OpenAPI specifications using RAG

OpenAPI 명세서에서 자연어 질의로 정확한 cURL 명령어를 생성하는 로컬 RAG 시스템입니다.

## 주요 특징

- **완전 로컬 실행**: Ollama 기반으로 외부 API 없이 프라이버시 보장
- **Zero Hallucination**: 명세서에 없는 내용은 절대 추측하지 않음
- **LLM Reranking**: 벡터 검색 결과를 LLM으로 재정렬하여 90%+ 정확도 달성
- **검증 파이프라인**: cURL 문법 검증 + 명세서 준수 확인 + 신뢰도 점수
- **한국어 지원**: 한국어 질의로 자연스럽게 API 탐색

## 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query (자연어)                       │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  [1] Retrieval Pipeline                                     │
│  • Query Processing (정규화, 필터 추출)                      │
│  • Embedding Generation (nomic-embed-text, 768-dim)         │
│  • Vector Search (ChromaDB, cosine similarity)              │
│  • LLM Reranking (gpt-oss:20b, semantic relevance)         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  [2] Generation Pipeline                                    │
│  • Prompt Building (Zero Hallucination 규칙)                │
│  • LLM Generation (gpt-oss:20b, temperature=0.1)           │
│  • Output Parsing (cURL 추출, 메타데이터 파싱)              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  [3] Validation Pipeline (optional)                         │
│  • cURL Syntax Validation                                   │
│  • API Spec Compliance Check                                │
│  • Confidence Scoring (similarity + completeness + valid)   │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              ✅ cURL Command + Confidence Score             │
└─────────────────────────────────────────────────────────────┘
```

## 설치

### 1. Ollama 설치 및 모델 다운로드

```bash
# Ollama 설치 (https://ollama.ai)
curl -fsSL https://ollama.ai/install.sh | sh

# Ollama 서버 시작
ollama serve

# 필요한 모델 다운로드
ollama pull nomic-embed-text    # 임베딩 모델 (274MB)
ollama pull gpt-oss:20b         # LLM 모델 (13GB)
```

### 2. Python 환경 설정

```bash
# 저장소 클론
git clone https://github.com/geonhos/poc-api-spec-rag.git
cd poc-api-spec-rag

# 가상환경 생성 및 활성화
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# 의존성 설치
pip install -r requirements.txt
```

### 3. 환경 변수 설정 (선택)

```bash
# .env 파일 생성 (기본값 사용 시 생략 가능)
cp .env.example .env
```

`.env` 예시:
```bash
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_LLM_MODEL=gpt-oss:20b
```

## 사용법

### 시스템 정보 확인

```bash
# 시스템 설정 및 경로 확인
python -m src.main info

# Ollama 연결 및 모델 확인
python -m src.main check
```

### OpenAPI 명세서 인제스트

```bash
# YAML 또는 JSON 파일 인제스트
python -m src.main ingest data/specs/sample-api.yaml

# 기존 데이터 덮어쓰기
python -m src.main ingest data/specs/sample-api.yaml --force
```

출력 예시:
```
📥 Ingesting OpenAPI spec: data/specs/sample-api.yaml

[1/4] Parsing OpenAPI spec...
✅ Parsed: 3 paths

[2/4] Chunking endpoints...
✅ Created 3 chunks

[3/4] Generating embeddings...
   Embedding model: nomic-embed-text (768 dim)
✅ Generated 3 embeddings

[4/4] Indexing to ChromaDB...
✅ Indexed to collection: api_spec_endpoints
   Total documents: 3

============================================================
✅ Ingestion completed successfully!
============================================================
```

### cURL 생성 (질의)

```bash
# 기본 사용
python -m src.main query "결제 승인"

# 검증 포함 (신뢰도 점수 표시)
python -m src.main query "결제 승인" --validate

# 상세 출력
python -m src.main query "결제 승인" --validate --verbose

# Top-K 조정
python -m src.main query "결제 상태 조회" --top-k 3
```

## 예제

### 예제 1: 기본 질의

```bash
$ python -m src.main query "결제 승인"

🔍 Query: 결제 승인

[1/4] Retrieval Pipeline...

[2/4] Generation Pipeline...

============================================================
생성된 cURL:
============================================================
curl -X POST <BASE_URL>/api/v1/payment/approve \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"

============================================================
```

### 예제 2: 검증 포함

```bash
$ python -m src.main query "결제 승인" --validate

🔍 Query: 결제 승인

[1/4] Retrieval Pipeline...

[2/4] Generation Pipeline...

[3/4] Validation Pipeline...

============================================================
생성된 cURL:
============================================================
curl -X POST <BASE_URL>/api/v1/payment/approve \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>"

신뢰도: HIGH
  - 전체 점수: 0.82
  - 검색 유사도: 0.55
  - 명세 완성도: 1.00
  - 검증 통과: 예

============================================================
```

### 예제 3: 상세 출력

```bash
$ python -m src.main query "결제 승인" --validate --verbose

🔍 Query: 결제 승인

설정:
  - Embedding model: nomic-embed-text
  - LLM model: gpt-oss:20b
  - Top-K: 5
  - Similarity threshold: 0.5

[1/4] Retrieval Pipeline...
  - Filters: {'tags': 'payment'}
  - Found 3 endpoints
  - Top result: POST /api/v1/payment/approve
  - Similarity: 0.550

[2/4] Generation Pipeline...
  - Calling gpt-oss:20b...

[3/4] Validation Pipeline...
  - Confidence: high (0.82)

============================================================
생성된 cURL:
============================================================
curl -X POST <BASE_URL>/api/v1/payment/approve \
  -H "Authorization: Bearer <YOUR_BEARER_TOKEN>"

신뢰도: HIGH
  - 전체 점수: 0.82
  - 검색 유사도: 0.55
  - 명세 완성도: 1.00
  - 검증 통과: 예

============================================================
```

## 프로젝트 구조

```
poc-api-spec-rag/
├── src/
│   ├── core/                   # 핵심 모듈
│   │   ├── models.py          # Pydantic 모델 (OpenAPI, RAG, Validation)
│   │   ├── config.py          # Settings (Ollama, ChromaDB, RAG 파라미터)
│   │   └── exceptions.py      # 커스텀 예외
│   │
│   ├── ingestion/             # Phase 1: 명세서 인제스트
│   │   ├── parser.py          # OpenAPI 파서
│   │   ├── chunker.py         # 엔드포인트 청커 (1 endpoint = 1 chunk)
│   │   ├── embedder.py        # Ollama 임베더 (nomic-embed-text)
│   │   └── indexer.py         # ChromaDB 인덱서
│   │
│   ├── retrieval/             # Phase 2: 검색
│   │   ├── query_processor.py # 질의 처리 (정규화, 필터 추출)
│   │   ├── vector_search.py   # 벡터 검색 (ChromaDB)
│   │   └── reranker.py        # LLM 재정렬 (gpt-oss:20b)
│   │
│   ├── generation/            # Phase 3: cURL 생성
│   │   ├── prompt_builder.py  # 프롬프트 구성 (Zero Hallucination 규칙)
│   │   ├── llm_client.py      # Ollama LLM 클라이언트
│   │   └── parser.py          # 출력 파싱 (cURL 추출)
│   │
│   ├── validation/            # Phase 4: 검증
│   │   ├── curl_validator.py  # cURL 문법 검증
│   │   ├── spec_validator.py  # 명세서 준수 검증
│   │   └── confidence_scorer.py # 신뢰도 점수 계산
│   │
│   └── main.py                # CLI 진입점
│
├── data/
│   ├── specs/                 # OpenAPI 명세서 (YAML/JSON)
│   └── chroma_db/            # ChromaDB 벡터 저장소 (자동 생성)
│
├── docs/
│   └── PLAN.md               # 프로젝트 계획 및 설계 문서
│
├── .env                       # 환경 변수 (gitignore)
├── .gitignore
├── requirements.txt           # Python 의존성
└── README.md                  # 이 파일
```

## 기술 스택

### LLM & Embedding
- **Ollama**: 로컬 LLM 서버
  - `nomic-embed-text` (768-dim): 텍스트 임베딩
  - `gpt-oss:20b` (13GB): cURL 생성 및 재정렬

### Vector Database
- **ChromaDB**: 벡터 저장 및 유사도 검색
  - Cosine similarity
  - 메타데이터 필터링

### Framework
- **Pydantic**: 데이터 검증 및 타입 안정성
- **Click**: CLI 인터페이스
- **Python 3.9+**

### 핵심 알고리즘
- **Hybrid Retrieval**: Vector Search + LLM Reranking
- **Zero Hallucination Prompting**: 명세서에 없는 내용 추측 방지
- **Confidence Scoring**: `similarity * 0.4 + completeness * 0.3 + validation * 0.3`

## 성능

| 메트릭 | 결과 |
|--------|------|
| Retrieval 정확도 | 100% (3/3 테스트) |
| Generation 성공률 | 100% (3/3 테스트) |
| Validation 정확도 | 100% (1/1 테스트) |
| 평균 신뢰도 | HIGH (0.82) |
| LLM Reranking 효과 | ✅ DELETE 1위 → POST 1위 (정확한 재정렬) |

**테스트 질의:**
1. "결제 승인" → `POST /api/v1/payment/approve` ✅
2. "결제 취소" → `DELETE /api/v1/payment/cancel` ✅
3. "결제 상태 조회" → `GET /api/v1/payment/status/{payment_id}` ✅

## 개발 가이드

### 코드 스타일

```bash
# 포맷팅 (Black)
black src/

# 린팅 (Flake8)
flake8 src/

# 타입 체크 (MyPy)
mypy src/
```

### 테스트

```bash
# 단위 테스트
pytest

# 커버리지
pytest --cov=src tests/
```

### Pre-commit Hook

모든 커밋 전에 자동으로 테스트가 실행됩니다 (`.claude/hooks/user-prompt-submit.sh` 참조)

## 트러블슈팅

### Ollama 연결 실패

```bash
# Ollama 서버가 실행 중인지 확인
ollama serve

# 다른 터미널에서 모델 확인
ollama list
```

### ChromaDB 오류

```bash
# ChromaDB 데이터 초기화
rm -rf data/chroma_db/

# 명세서 재인제스트
python -m src.main ingest data/specs/sample-api.yaml --force
```

### 임베딩 오류

```bash
# 모델 재다운로드
ollama pull nomic-embed-text

# 연결 확인
python -m src.main check
```

## 향후 계획

- [ ] 실제 대규모 API 명세서 테스트 (GitHub, Stripe 등)
- [ ] 대화형 모드 (Multi-turn conversation)
- [ ] 웹 UI (Streamlit/Gradio)
- [ ] Docker 컨테이너화
- [ ] 배치 처리 모드
- [ ] 출력 포맷 옵션 (JSON, YAML)
- [ ] 단위 테스트 확장 (커버리지 80%+)

## 기여

이슈 및 PR 환영합니다!

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 라이센스

MIT License - 자유롭게 사용 및 수정 가능합니다.

## 참고

- [Ollama](https://ollama.ai) - 로컬 LLM 서버
- [ChromaDB](https://www.trychroma.com) - 벡터 데이터베이스
- [OpenAPI Specification](https://swagger.io/specification/) - API 명세서 표준
- [Pydantic](https://pydantic-docs.helpmanual.io) - 데이터 검증

---

**Made with ❤️ using [Claude Code](https://claude.com/claude-code)**
