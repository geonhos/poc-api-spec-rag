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
    click.echo(f"📥 Ingesting OpenAPI spec: {spec_file}")

    spec_path = Path(spec_file)

    if force:
        click.echo("⚠️  Force mode: 기존 데이터를 덮어씁니다")

    # TODO: Phase 1에서 구현
    click.echo("❌ Not implemented yet (Phase 1)")
    click.echo(f"   Spec file: {spec_path.absolute()}")
    click.echo(f"   Target DB: {settings.CHROMA_DB_DIR}")


@cli.command()
@click.argument("query")
@click.option("--top-k", default=5, help="검색할 엔드포인트 개수")
@click.option("--verbose", "-v", is_flag=True, help="상세 출력")
def query(query: str, top_k: int, verbose: bool):
    """자연어 질의로 cURL 명령어를 생성합니다.

    Examples:
        $ python -m src.main query "결제 승인 API curl 만들어줘"
        $ python -m src.main query "사용자 정보 조회" --top-k 3 --verbose
    """
    click.echo(f"🔍 Query: {query}")
    click.echo(f"📊 Top-K: {top_k}")

    if verbose:
        click.echo(f"\n설정:")
        click.echo(f"  - Embedding model: {settings.OLLAMA_EMBEDDING_MODEL}")
        click.echo(f"  - LLM model: {settings.OLLAMA_LLM_MODEL}")
        click.echo(f"  - Similarity threshold: {settings.SIMILARITY_THRESHOLD}")

    # TODO: Phase 2-4에서 구현
    click.echo("\n❌ Not implemented yet (Phase 2-4)")
    click.echo("   Pipeline: Query → Retrieval → Generation → Validation")


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
