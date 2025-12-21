"""Main CLI for poc-api-spec-rag."""

import click
from pathlib import Path
from src.core import settings


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """RAG-based API Specification Assistant

    OpenAPI 명세서에서 정확한 cURL 명령어를 생성합니다.
    """
    pass


@cli.command()
@click.argument("spec_file", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="기존 데이터 덮어쓰기")
def ingest(spec_file: str, force: bool):
    """OpenAPI 명세서를 인제스트합니다.

    Examples:
        $ python -m src.main ingest ./specs/payment-api.yaml
        $ python -m src.main ingest ./specs/user-api.json --force
    """
    from src.ingestion import OpenAPIParser, EndpointChunker, OllamaEmbedder, ChromaIndexer

    click.echo(f"📥 Ingesting OpenAPI spec: {spec_file}")

    spec_path = Path(spec_file)

    if force:
        click.echo("⚠️  Force mode: 기존 데이터를 덮어씁니다")

    try:
        # 1. OpenAPI 파싱
        click.echo("\n[1/4] Parsing OpenAPI spec...")
        parser = OpenAPIParser()
        spec = parser.parse_file(spec_path)
        parser.validate_spec(spec)
        click.echo(f"✅ Parsed: {len(spec.paths)} paths")

        # 2. 엔드포인트 청킹
        click.echo("\n[2/4] Chunking endpoints...")
        chunker = EndpointChunker()
        chunks = chunker.chunk_spec(spec)
        click.echo(f"✅ Created {len(chunks)} chunks")

        # 3. 임베딩 생성
        click.echo("\n[3/4] Generating embeddings...")
        embedder = OllamaEmbedder()

        # 임베딩 차원 확인
        dim = embedder.get_embedding_dimension()
        click.echo(f"   Embedding model: {embedder.model} ({dim} dim)")

        # 배치 임베딩 생성
        embeddings = embedder.embed_chunks(chunks)
        click.echo(f"✅ Generated {len(embeddings)} embeddings")

        # 4. ChromaDB 저장
        click.echo("\n[4/4] Indexing to ChromaDB...")
        indexer = ChromaIndexer(reset=force)
        indexer.index_chunks(chunks, embeddings)

        # 저장 결과 확인
        info = indexer.get_collection_info()
        click.echo(f"✅ Indexed to collection: {info['name']}")
        click.echo(f"   Total documents: {info['count']}")

        click.echo("\n" + "=" * 60)
        click.echo("✅ Ingestion completed successfully!")
        click.echo("=" * 60)

    except Exception as e:
        click.echo(f"\n❌ Ingestion failed: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.argument("query")
@click.option("--top-k", default=5, help="검색할 엔드포인트 개수")
@click.option("--verbose", "-v", is_flag=True, help="상세 출력")
@click.option("--validate", is_flag=True, help="검증 활성화")
def query(query: str, top_k: int, verbose: bool, validate: bool):
    """자연어 질의로 cURL 명령어를 생성합니다.

    Examples:
        $ python -m src.main query "결제 승인 API curl 만들어줘"
        $ python -m src.main query "사용자 정보 조회" --top-k 3 --verbose
        $ python -m src.main query "결제 승인" --validate
    """
    from src.retrieval import QueryProcessor, VectorSearcher, LLMReranker
    from src.generation import PromptBuilder, OllamaLLMClient, OutputParser
    from src.validation import CurlValidator, SpecValidator, ConfidenceScorer

    click.echo(f"🔍 Query: {query}")

    if verbose:
        click.echo(f"\n설정:")
        click.echo(f"  - Embedding model: {settings.OLLAMA_EMBEDDING_MODEL}")
        click.echo(f"  - LLM model: {settings.OLLAMA_LLM_MODEL}")
        click.echo(f"  - Top-K: {top_k}")
        click.echo(f"  - Similarity threshold: {settings.SIMILARITY_THRESHOLD}")

    try:
        # [1/4] Retrieval Pipeline
        click.echo("\n[1/4] Retrieval Pipeline...")
        processor = QueryProcessor()
        searcher = VectorSearcher()
        reranker = LLMReranker()

        # 질의 처리
        query_req = processor.process_query(query, top_k=top_k)
        if verbose:
            click.echo(f"  - Filters: {query_req.filters}")

        # 임베딩 생성
        query_embedding = processor.embed_query(query)

        # 벡터 검색
        retrieval_resp = searcher.search(query_embedding, query_req)
        if not retrieval_resp.results:
            click.echo("❌ 관련 엔드포인트를 찾지 못했습니다")
            return

        if verbose:
            click.echo(f"  - Found {len(retrieval_resp.results)} endpoints")

        # LLM 재정렬
        reranked_results = reranker.rerank(query, retrieval_resp.results, top_n=1)
        top_result = reranked_results[0]

        if verbose:
            click.echo(f"  - Top result: {top_result.chunk.metadata.method} {top_result.chunk.metadata.endpoint}")
            click.echo(f"  - Similarity: {top_result.similarity_score:.3f}")

        # [2/4] Generation Pipeline
        click.echo("\n[2/4] Generation Pipeline...")
        builder = PromptBuilder()
        llm = OllamaLLMClient()
        parser = OutputParser()

        # 프롬프트 구성
        gen_req = builder.build_prompt(query, [top_result.chunk])
        user_prompt = builder._build_user_prompt(gen_req.query, gen_req.retrieved_chunks)

        # LLM 생성
        if verbose:
            click.echo(f"  - Calling {settings.OLLAMA_LLM_MODEL}...")
        llm_output = llm.generate(gen_req.system_prompt, user_prompt)

        # 출력 파싱
        source_endpoint = f"{top_result.chunk.metadata.method} {top_result.chunk.metadata.endpoint}"
        gen_resp = parser.parse_curl_response(llm_output, source_endpoint)

        if not gen_resp.curl_command.command:
            click.echo("\n❌ cURL 생성 실패")
            if gen_resp.curl_command.explanation:
                click.echo(f"사유: {gen_resp.curl_command.explanation}")
            if gen_resp.warnings:
                click.echo("\n⚠️  경고:")
                for warn in gen_resp.warnings:
                    click.echo(f"  - {warn}")
            return

        # [3/4] Validation Pipeline (옵션)
        confidence = None
        if validate:
            click.echo("\n[3/4] Validation Pipeline...")
            curl_val = CurlValidator()
            spec_val = SpecValidator()
            scorer = ConfidenceScorer()

            # cURL 문법 검증
            syntax_valid, syntax_errors = curl_val.validate(gen_resp.curl_command.command)
            if verbose and syntax_errors:
                click.echo(f"  - Syntax errors: {syntax_errors}")

            # 명세 준수 검증
            curl_components = curl_val.get_curl_components(gen_resp.curl_command.command)
            spec_valid, spec_warnings, spec_completeness = spec_val.validate(
                curl_components, top_result.chunk
            )

            if verbose and spec_warnings:
                click.echo(f"  - Spec warnings: {spec_warnings}")

            # 신뢰도 계산
            confidence = scorer.calculate_score(
                similarity=top_result.similarity_score,
                spec_completeness=spec_completeness,
                syntax_valid=syntax_valid,
                spec_valid=spec_valid,
            )

            if verbose:
                click.echo(f"  - Confidence: {confidence.level} ({confidence.overall:.2f})")

        # [4/4] 결과 출력
        click.echo("\n" + "=" * 60)
        click.echo("생성된 cURL:")
        click.echo("=" * 60)
        click.echo(gen_resp.curl_command.command)

        if gen_resp.curl_command.explanation:
            click.echo(f"\n설명:")
            click.echo(gen_resp.curl_command.explanation)

        if gen_resp.curl_command.required_params:
            click.echo(f"\n필수 입력:")
            for param in gen_resp.curl_command.required_params:
                click.echo(f"  - {param}")

        if gen_resp.curl_command.expected_responses:
            click.echo(f"\n예상 응답:")
            for code, desc in gen_resp.curl_command.expected_responses.items():
                click.echo(f"  - {code}: {desc}")

        # 신뢰도 표시 (--validate 옵션)
        if confidence:
            click.echo(f"\n신뢰도: {confidence.level.upper()}")
            click.echo(f"  - 전체 점수: {confidence.overall:.2f}")
            click.echo(f"  - 검색 유사도: {confidence.similarity:.2f}")
            click.echo(f"  - 명세 완성도: {confidence.spec_completeness:.2f}")
            click.echo(f"  - 검증 통과: {'예' if confidence.validation_passed else '아니오'}")

        # 경고 메시지
        if gen_resp.warnings:
            click.echo("\n⚠️  경고:")
            for warn in gen_resp.warnings:
                click.echo(f"  - {warn}")

        click.echo("\n" + "=" * 60)

    except Exception as e:
        click.echo(f"\n❌ Query failed: {e}", err=True)
        if verbose:
            import traceback
            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


@cli.command()
def info():
    """시스템 정보를 출력합니다."""
    click.echo("=" * 60)
    click.echo("API Spec RAG - System Information")
    click.echo("=" * 60)

    click.echo(f"\n📂 Directories:")
    click.echo(f"  Project Root: {settings.PROJECT_ROOT}")
    click.echo(f"  Data Dir: {settings.DATA_DIR}")
    click.echo(f"  Specs Dir: {settings.SPECS_DIR}")
    click.echo(f"  ChromaDB Dir: {settings.CHROMA_DB_DIR}")

    click.echo(f"\n🤖 Models:")
    click.echo(f"  Embedding: {settings.OLLAMA_EMBEDDING_MODEL} (768 dim)")
    click.echo(f"  LLM: {settings.OLLAMA_LLM_MODEL}")
    click.echo(f"  Ollama URL: {settings.OLLAMA_BASE_URL}")

    click.echo(f"\n⚙️  RAG Settings:")
    click.echo(f"  Top-K: {settings.TOP_K}")
    click.echo(f"  Similarity Threshold: {settings.SIMILARITY_THRESHOLD}")
    click.echo(f"  High Confidence Threshold: {settings.HIGH_CONFIDENCE_THRESHOLD}")

    click.echo("\n" + "=" * 60)


@cli.command()
@click.option("--host", default="localhost", help="Ollama 호스트")
@click.option("--port", default=11434, help="Ollama 포트")
def check(host: str, port: int):
    """Ollama 연결을 확인합니다."""
    import ollama

    click.echo(f"🔌 Checking Ollama connection: {host}:{port}")

    try:
        # 모델 목록 조회
        result = ollama.list()
        models = result.get("models", [])

        click.echo(f"✅ Ollama 서버 연결 성공")
        click.echo(f"\n설치된 모델 ({len(models)}개):")

        for model in models:
            name = model.get("name", "unknown")
            size = model.get("size", 0) / (1024**3)  # GB
            click.echo(f"  - {name} ({size:.1f} GB)")

        # 필요한 모델 확인
        model_names = [m.get("name") for m in models]

        click.echo(f"\n필수 모델 확인:")
        embedding_ok = settings.OLLAMA_EMBEDDING_MODEL in model_names
        llm_ok = settings.OLLAMA_LLM_MODEL in model_names

        click.echo(f"  Embedding ({settings.OLLAMA_EMBEDDING_MODEL}): {'✅' if embedding_ok else '❌'}")
        click.echo(f"  LLM ({settings.OLLAMA_LLM_MODEL}): {'✅' if llm_ok else '❌'}")

        if not (embedding_ok and llm_ok):
            click.echo(f"\n⚠️  필요한 모델이 설치되지 않았습니다")
            if not embedding_ok:
                click.echo(f"   $ ollama pull {settings.OLLAMA_EMBEDDING_MODEL}")
            if not llm_ok:
                click.echo(f"   $ ollama pull {settings.OLLAMA_LLM_MODEL}")

    except Exception as e:
        click.echo(f"❌ Ollama 연결 실패: {e}")
        click.echo(f"\n💡 Ollama가 실행 중인지 확인하세요:")
        click.echo(f"   $ ollama serve")


def main():
    """Main entry point."""
    cli()


if __name__ == "__main__":
    main()
