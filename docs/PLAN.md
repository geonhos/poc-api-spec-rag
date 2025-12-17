# POC API Spec RAG - 구현 계획

**버전**: 1.0
**작성일**: 2024-12-17
**상태**: 설계 단계

---

## 목표

OpenAPI 명세서를 기반으로 자연어 질의에 대해 정확한 cURL 명령어를 생성하는 RAG 시스템 구축

**핵심 원칙**: 명세서에 없는 정보는 절대 추측하지 않음 (Zero Hallucination)

---

## 1. 시스템 아키텍처

```
사용자 질의 ("결제 승인 API curl 만들어줘")
    ↓
[Query Processing]
    - 질의 임베딩 생성
    ↓
[RAG Retrieval]
    - ChromaDB에서 유사한 엔드포인트 검색 (Top-K=5)
    - 메타데이터 필터링 (method, tags)
    ↓
[Context Assembly]
    - 검색된 명세서 청크 조합
    ↓
[LLM Generation]
    - Claude API 호출 (strict prompt)
    - cURL 명령어 생성
    ↓
[Validation]
    - cURL 문법 검증
    - 명세서 준수 확인
    - 신뢰도 점수 계산
    ↓
결과 반환 (cURL 또는 "정보 부족" 메시지)
```

---

## 2. 청킹 전략

### 엔드포인트 중심 청킹
- **단위**: 1 엔드포인트 = 1 청크 (path + method 조합)
- **이유**: cURL 생성에 필요한 완전한 컨텍스트 제공

**청크 구조**:
```json
{
  "chunk_id": "POST_/api/v1/payment/approve",
  "content": {
    "method": "POST",
    "path": "/api/v1/payment/approve",
    "summary": "결제 승인",
    "parameters": [...],
    "requestBody": {...},
    "responses": {...}
  },
  "metadata": {
    "method": "POST",
    "tags": ["payment"],
    "requires_auth": true
  }
}
```

---

## 3. 임베딩 및 벡터 저장

### 임베딩
- **모델**: OpenAI `text-embedding-3-small` (1536 dim)
- **임베딩 내용**: `[METHOD] [PATH] - [SUMMARY]\nDescription: ...\nParameters: ...\nTags: ...`

### 벡터 DB
- **DB**: ChromaDB
- **검색 전략**:
  - Semantic search (Top-K=5)
  - 메타데이터 필터링 (method, tags)
  - 유사도 임계값: 0.5 이상

**신뢰도 기준**:
- `> 0.7`: High confidence
- `0.5 - 0.7`: Medium confidence
- `< 0.5`: Reject

---

## 4. 프롬프트 구조

### System Prompt (핵심)
```
당신은 OpenAPI 명세서에서 정확한 cURL 명령어를 생성하는 전문가입니다.

필수 규칙:
1. 제공된 명세서에만 기반하여 cURL 생성
2. 명세서에 없는 파라미터나 값을 절대 추측하지 않음
3. 필수 정보가 없으면 명시적으로 "정보 부족: [항목]" 반환
4. 플레이스홀더 사용 (<payment_id>, <YOUR_API_KEY>)
5. 필수/선택 파라미터 구분 명확히

출력 형식:
- 실행 가능한 cURL 명령어
- 각 파라미터 설명
- 예상 응답 코드
- 신뢰도 수준 (high/medium/low)
```

### User Prompt Template
```
명세서:
---
{retrieved_chunks}
---

사용자 질의: {user_query}

위 명세서를 기반으로 cURL 명령어를 생성하세요.
필수 정보가 없으면 "cURL 생성 불가: [이유]"를 반환하세요.
```

---

## 5. 검증 및 오류 처리

### Pre-Generation 검증
```python
if max_similarity < 0.5:
    return "일치하는 엔드포인트 없음"
elif max_similarity < 0.7:
    return "낮은 신뢰도. 다음을 의미하나요: [endpoint]?"
```

### Post-Generation 검증
1. **cURL 문법 검증**: `curl` 명령어, URL 형식, 헤더 형식
2. **명세서 준수 확인**:
   - HTTP method 일치
   - 필수 파라미터 포함 여부
   - Content-Type 일치
3. **신뢰도 계산**:
   ```python
   score = similarity * 0.4 + spec_completeness * 0.3 + validation * 0.3
   ```

### 실패 처리

| 실패 유형 | 대응 |
|----------|------|
| 엔드포인트 미발견 | "일치하는 엔드포인트 없음. 사용 가능: [목록]" |
| 모호한 질의 | "여러 결과 발견: [목록]. 구체적으로 지정하세요" |
| 필수 파라미터 누락 | "엔드포인트는 있으나 파라미터 스키마 누락: [목록]" |
| LLM 환각 | 검증 실패 → 재시도 (stricter prompt) |

---

## 6. 프로젝트 구조

```
poc-api-spec-rag/
├── src/
│   ├── ingestion/              # OpenAPI 명세서 처리
│   │   ├── parser.py           # yaml/json 파싱
│   │   ├── chunker.py          # 엔드포인트 청킹
│   │   ├── embedder.py         # 임베딩 생성
│   │   └── indexer.py          # ChromaDB 저장
│   │
│   ├── retrieval/              # 검색
│   │   ├── query_processor.py # 질의 처리
│   │   └── vector_search.py   # 벡터 검색
│   │
│   ├── generation/             # cURL 생성
│   │   ├── prompt_builder.py  # 프롬프트 구성
│   │   ├── llm_client.py      # Claude API
│   │   └── parser.py           # 출력 파싱
│   │
│   ├── validation/             # 검증
│   │   ├── curl_validator.py  # 문법 검증
│   │   ├── spec_validator.py  # 명세서 준수
│   │   └── confidence.py       # 신뢰도 계산
│   │
│   ├── core/
│   │   ├── config.py           # 설정
│   │   ├── models.py           # Pydantic 모델
│   │   └── exceptions.py       # 예외 정의
│   │
│   └── main.py                 # CLI
│
├── tests/
│   ├── unit/                   # 단위 테스트
│   ├── integration/            # 통합 테스트
│   └── fixtures/               # 테스트 데이터
│
├── data/                       # 런타임 데이터 (gitignored)
│   ├── specs/                  # OpenAPI 명세서
│   └── chroma_db/              # ChromaDB 저장소
│
├── docs/
├── scripts/
│   ├── ingest_spec.py          # 명세서 인제스트
│   └── query_cli.py            # 질의 CLI
│
└── requirements.txt
```

---

## 7. 주요 리스크 및 완화

| 리스크 | 완화 전략 |
|--------|----------|
| **LLM 환각** | strict prompt, post-validation, 신뢰도 점수, few-shot |
| **검색 품질 저하** | 고품질 임베딩, 메타데이터 필터, 유사도 임계값, reranking |
| **불완전한 명세서** | 명세서 검증, 누락 필드 표시, 경고 메시지 |
| **모호한 질의** | 의도 감지, 명확화 질문, 신뢰도 점수 |
| **토큰 제한** | 작은 청크 단위, Top-K 제한, Claude 3.5 Sonnet (200K) |
| **명세서 버전 드리프트** | 버전 추적, 해시 비교, 증분 업데이트 |

---

## 8. 구현 단계

### Phase 0: 기반 구축 (Week 1)
- [x] 프로젝트 구조 생성
- [x] 의존성 설치
- [ ] Pydantic 모델 정의
- [ ] CLI 스켈레톤

### Phase 1: Ingestion Pipeline (Week 1-2)
- [ ] OpenAPI 파서
- [ ] 엔드포인트 청커
- [ ] 임베딩 생성기
- [ ] ChromaDB 인덱서
- [ ] 단위 테스트

**인수 기준**: 샘플 명세서 파싱 → 청킹 → ChromaDB 저장

### Phase 2: Retrieval Pipeline (Week 2)
- [ ] 질의 프로세서
- [ ] 벡터 검색
- [ ] 메타데이터 필터링
- [ ] 테스트

**인수 기준**: 질의 → Top-K 엔드포인트 검색

### Phase 3: Generation Pipeline (Week 3)
- [ ] 프롬프트 빌더
- [ ] Claude API 클라이언트
- [ ] 에러 핸들링

**인수 기준**: 검색 결과 → cURL 생성

### Phase 4: Validation (Week 3)
- [ ] cURL 검증기
- [ ] 명세서 준수 검증기
- [ ] 신뢰도 계산
- [ ] 테스트

**인수 기준**: 잘못된 cURL 거부, 신뢰도 정확도

### Phase 5: 통합 (Week 4)
- [ ] 모든 모듈 통합
- [ ] E2E 테스트
- [ ] 성능 테스트

**인수 기준**: 질의 → cURL 생성 (정확도 90%+, 레이턴시 <5s)

### Phase 6: 개선 (Week 4+)
- [ ] 로깅, 모니터링
- [ ] 에러 메시지 개선
- [ ] 문서화

---

## 9. 성공 지표

### 정확도
- cURL 정확도: **95%**
- 환각 없음: **100%** (추측 금지)
- 검색 정밀도: **90%** (Top-1 정확도)
- 명세서 준수: **100%**

### 성능
- 전체 레이턴시: **< 5초**
- 벡터 검색: **< 500ms**
- LLM 생성: **< 3초**

### 품질
- 명확화 필요 비율: **< 10%**
- 신뢰도 정확도: **85%**

---

## 10. 핵심 의존성

```python
# LLM & 임베딩
anthropic>=0.18.0
openai>=1.0.0

# 벡터 DB
chromadb>=0.4.0

# 데이터 처리
pydantic>=2.0.0
pyyaml>=6.0.0
httpx>=0.25.0

# CLI
click>=8.0.0

# 테스트
pytest>=7.0.0
pytest-cov>=4.0.0
```

---

## 11. 용어

| 용어 | 설명 |
|------|------|
| **청크** | 벡터로 저장되는 명세서 단위 (엔드포인트 또는 스키마) |
| **임베딩** | 텍스트의 벡터 표현 (1536차원) |
| **Top-K** | 가장 유사한 K개 청크 검색 (K=5) |
| **유사도 점수** | 질의-청크 간 코사인 유사도 (0-1) |
| **환각** | LLM이 컨텍스트에 없는 정보 생성 |
| **신뢰도 점수** | 생성된 cURL 정확도 추정 (high/medium/low) |

---

**End of Plan**
