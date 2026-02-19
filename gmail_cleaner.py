"""Gmail Auto Cleaner — 자동으로 분류·라벨링·아카이브·삭제를 처리합니다."""

import sys
import time
from dataclasses import dataclass, field
from typing import Optional

import click
from googleapiclient.errors import HttpError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
from rich.table import Table
from rich import box

from auth import get_gmail_service

console = Console()

MAX_RESULTS_PER_PAGE = 500
BATCH_SIZE = 50


# ---------------------------------------------------------------------------
# Auto rules definition
# ---------------------------------------------------------------------------

@dataclass
class AutoRule:
    name: str
    description: str
    query: str
    action: str          # "delete" or "archive"
    label: Optional[str] = None
    safe: bool = False   # True → 자동 처리(아카이브), False → 확인 후 처리(삭제)


# 규칙 순서: 삭제 그룹 먼저, 아카이브 그룹 나중
AUTO_RULES: list[AutoRule] = [
    AutoRule(
        name="Newsletter",
        description="뉴스레터 / 구독 메일",
        query="unsubscribe in:inbox",
        label="AutoClean/Newsletter",
        action="delete",
        safe=False,
    ),
    AutoRule(
        name="Promotion",
        description="프로모션 메일",
        query="category:promotions",
        label="AutoClean/Promotion",
        action="delete",
        safe=False,
    ),
    AutoRule(
        name="Social",
        description="소셜 / SNS 알림 메일",
        query="category:social",
        label="AutoClean/Social",
        action="delete",
        safe=False,
    ),
    AutoRule(
        name="NoReply",
        description="발신 전용(noreply) 메일",
        query="(from:noreply OR from:no-reply OR from:donotreply) in:inbox",
        label="AutoClean/NoReply",
        action="archive",
        safe=True,
    ),
    AutoRule(
        name="OldMail",
        description="1년 이상 된 메일",
        query="older_than:365d in:inbox",
        label="AutoClean/OldMail",
        action="archive",
        safe=True,
    ),
]


# ---------------------------------------------------------------------------
# Gmail label helpers
# ---------------------------------------------------------------------------

def get_or_create_label(service, label_name: str) -> str:
    """라벨이 없으면 생성하고 ID를 반환합니다."""
    result = service.users().labels().list(userId="me").execute()
    for lbl in result.get("labels", []):
        if lbl["name"] == label_name:
            return lbl["id"]

    created = service.users().labels().create(
        userId="me",
        body={
            "name": label_name,
            "labelListVisibility": "labelShow",
            "messageListVisibility": "show",
        },
    ).execute()
    return created["id"]


def apply_label_batch(service, msg_ids: list[str], label_id: str):
    """메시지 목록에 라벨을 배치로 적용합니다."""
    for i in range(0, len(msg_ids), BATCH_SIZE):
        batch = msg_ids[i : i + BATCH_SIZE]
        service.users().messages().batchModify(
            userId="me",
            body={"ids": batch, "addLabelIds": [label_id]},
        ).execute()
        time.sleep(0.05)


# ---------------------------------------------------------------------------
# Gmail API helpers
# ---------------------------------------------------------------------------

def fetch_message_ids(service, query: str, max_results: Optional[int] = None) -> list[str]:
    """Gmail 검색 쿼리에 매칭되는 메시지 ID 전체를 반환합니다."""
    ids: list[str] = []
    page_token = None

    while True:
        kwargs: dict = {
            "userId": "me",
            "q": query,
            "maxResults": MAX_RESULTS_PER_PAGE,
        }
        if page_token:
            kwargs["pageToken"] = page_token

        result = service.users().messages().list(**kwargs).execute()
        messages = result.get("messages", [])
        ids.extend(m["id"] for m in messages)

        if max_results and len(ids) >= max_results:
            ids = ids[:max_results]
            break

        page_token = result.get("nextPageToken")
        if not page_token:
            break

    return ids


def get_message_snippet(service, msg_id: str) -> dict:
    """메시지의 발신자·제목·날짜를 가져옵니다."""
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["From", "Subject", "Date"],
    ).execute()
    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": msg_id,
        "from": headers.get("From", "(알 수 없음)"),
        "subject": headers.get("Subject", "(제목 없음)"),
        "date": headers.get("Date", ""),
    }


def batch_delete(service, msg_ids: list[str]) -> int:
    """메시지를 배치로 삭제(휴지통 이동)합니다."""
    deleted = 0
    batches = [msg_ids[i : i + BATCH_SIZE] for i in range(0, len(msg_ids), BATCH_SIZE)]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  삭제 중...", total=len(batches))
        for batch in batches:
            service.users().messages().batchDelete(
                userId="me",
                body={"ids": batch},
            ).execute()
            deleted += len(batch)
            progress.advance(task)
            time.sleep(0.1)

    return deleted


def batch_archive(service, msg_ids: list[str]) -> int:
    """메시지를 배치로 아카이브(받은편지함에서 제거)합니다."""
    archived = 0
    batches = [msg_ids[i : i + BATCH_SIZE] for i in range(0, len(msg_ids), BATCH_SIZE)]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("  아카이브 중...", total=len(batches))
        for batch in batches:
            service.users().messages().batchModify(
                userId="me",
                body={"ids": batch, "removeLabelIds": ["INBOX"]},
            ).execute()
            archived += len(batch)
            progress.advance(task)
            time.sleep(0.1)

    return archived


def show_all_emails(service, msg_ids: list[str]):
    """삭제 대상 메시지 전체를 테이블로 출력합니다."""
    rows = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task(
            f"  목록 조회 중... (총 {len(msg_ids)}개)", total=len(msg_ids)
        )
        for mid in msg_ids:
            try:
                info = get_message_snippet(service, mid)
                rows.append((info["from"], info["subject"], info["date"]))
            except HttpError:
                rows.append(("(조회 오류)", "", ""))
            progress.advance(task)

    table = Table(box=box.SIMPLE, show_lines=False, padding=(0, 1))
    table.add_column("No.", style="dim", width=5, justify="right")
    table.add_column("발신자", style="cyan", max_width=40, no_wrap=True)
    table.add_column("제목", style="white", max_width=50, no_wrap=True)
    table.add_column("날짜", style="dim", max_width=25)

    for i, (sender, subject, date) in enumerate(rows, 1):
        table.add_row(str(i), sender, subject, date)

    console.print(table)


# ---------------------------------------------------------------------------
# Auto pipeline
# ---------------------------------------------------------------------------

@dataclass
class RuleResult:
    rule: AutoRule
    ids: list[str] = field(default_factory=list)


def run_auto_pipeline(service, dry_run: bool):
    """자동 분류 → 라벨 적용 → 아카이브 → 삭제 확인 파이프라인."""

    # ── Phase 1: 스캔 및 분류 ─────────────────────────────────────────────
    console.print()
    console.print(Panel(
        "[bold]Phase 1[/bold]  받은편지함을 자동으로 스캔합니다.",
        border_style="dim blue", padding=(0, 1),
    ))

    results: list[RuleResult] = []

    for rule in AUTO_RULES:
        with console.status(f"  스캔 중: [cyan]{rule.description}[/cyan]"):
            ids = fetch_message_ids(service, rule.query)

        rr = RuleResult(rule=rule, ids=ids)
        results.append(rr)

        if not rule.safe:
            action_tag = "[bold red]삭제 예정[/bold red] [dim](확인 필요)[/dim]"
        else:
            action_tag = "[bold yellow]자동 아카이브[/bold yellow]"

        count_tag = f"[bold]{len(ids):>6}개[/bold]" if ids else "[dim]     0개[/dim]"
        console.print(f"  [green]✓[/green]  {rule.description:<26}  {count_tag}  →  {action_tag}")

    # 아무것도 없으면 종료
    if all(not r.ids for r in results):
        console.print("\n[green]받은편지함이 깨끗합니다. 처리할 메일이 없습니다.[/green]")
        return

    # ── Phase 2: 라벨 적용 ────────────────────────────────────────────────
    label_rules = [r for r in results if r.rule.label and r.ids]

    if label_rules:
        console.print()
        console.print(Panel(
            "[bold]Phase 2[/bold]  Gmail 라벨을 생성하고 적용합니다.",
            border_style="dim blue", padding=(0, 1),
        ))

        for rr in label_rules:
            if dry_run:
                console.print(
                    f"  [yellow][DRY RUN][/yellow] {rr.rule.label}  "
                    f"→  {len(rr.ids)}개 (스킵)"
                )
                continue

            with console.status(f"  라벨 적용 중: [cyan]{rr.rule.label}[/cyan]"):
                label_id = get_or_create_label(service, rr.rule.label)
                apply_label_batch(service, rr.ids, label_id)

            console.print(
                f"  [green]✓[/green]  [cyan]{rr.rule.label}[/cyan]  "
                f"→  {len(rr.ids)}개 적용 완료"
            )

    # ── Phase 3: 안전한 작업 자동 처리 (아카이브) ─────────────────────────
    safe_results = [r for r in results if r.rule.safe and r.ids]

    if safe_results:
        console.print()
        console.print(Panel(
            "[bold]Phase 3[/bold]  안전한 작업을 자동으로 처리합니다 (아카이브).",
            border_style="dim blue", padding=(0, 1),
        ))

        for rr in safe_results:
            if dry_run:
                console.print(
                    f"  [yellow][DRY RUN][/yellow] {rr.rule.description}  "
                    f"→  {len(rr.ids)}개 아카이브 (스킵)"
                )
                continue

            console.print(f"\n  [cyan]{rr.rule.description}[/cyan]  {len(rr.ids)}개")
            archived = batch_archive(service, rr.ids)
            console.print(f"  [green]✓[/green]  {archived}개 아카이브 완료")

    # ── Phase 4: 삭제 — 그룹별 미리보기 및 확인 ─────────────────────────
    delete_results = [r for r in results if not r.rule.safe and r.ids]

    if delete_results:
        console.print()
        console.print(Panel(
            "[bold]Phase 4[/bold]  삭제 작업입니다. 그룹별로 확인 후 처리합니다.",
            border_style="dim red", padding=(0, 1),
        ))

        # 동일 메일이 여러 삭제 그룹에 중복 포함되는 것을 방지
        seen_delete_ids: set[str] = set()
        total_deleted = 0
        total_skipped = 0

        for idx, rr in enumerate(delete_results, 1):
            ids_to_delete = [mid for mid in rr.ids if mid not in seen_delete_ids]
            if not ids_to_delete:
                continue

            console.print(
                f"\n  [bold]그룹 {idx}/{len(delete_results)}[/bold]  "
                f"[cyan]{rr.rule.description}[/cyan]  "
                f"→  [bold red]{len(ids_to_delete)}개[/bold red] 삭제 예정\n"
            )
            show_all_emails(service, ids_to_delete)

            if dry_run:
                console.print(f"  [yellow][DRY RUN][/yellow] {len(ids_to_delete)}개 삭제 (스킵)\n")
                seen_delete_ids.update(ids_to_delete)
                total_skipped += len(ids_to_delete)
                continue

            if Confirm.ask(f"  [bold red]{len(ids_to_delete)}개[/bold red]를 삭제하시겠습니까?"):
                deleted = batch_delete(service, ids_to_delete)
                seen_delete_ids.update(ids_to_delete)
                total_deleted += deleted
                console.print(f"  [green]✓[/green]  {deleted}개 삭제 완료\n")
            else:
                console.print(f"  [dim]건너뜀: {rr.rule.description}[/dim]\n")
                total_skipped += len(ids_to_delete)

    # ── 요약 ─────────────────────────────────────────────────────────────
    console.print()
    console.print("─" * 58)

    summary = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    summary.add_column("항목", style="dim", width=20)
    summary.add_column("결과", style="bold white", justify="right")

    total_labeled = sum(len(r.ids) for r in results if r.rule.label)
    total_archived = sum(len(r.ids) for r in results if r.rule.safe)
    total_found = sum(len(r.ids) for r in results if not r.rule.safe)

    mode_note = " [yellow](DRY RUN — 실제 처리 없음)[/yellow]" if dry_run else ""
    summary.add_row("라벨 적용", f"{total_labeled}개")
    summary.add_row("아카이브", f"{total_archived}개{mode_note}")
    summary.add_row("삭제 대상", f"{total_found}개{mode_note}")

    console.print(Panel(
        summary,
        title="[bold green]완료[/bold green]",
        border_style="green",
    ))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

@click.command()
@click.option(
    "--dry-run", is_flag=True, default=False,
    help="실제 변경 없이 결과만 미리 확인합니다.",
)
def main(dry_run: bool):
    """Gmail 자동 정리 도구 — 분류·라벨링·아카이브·삭제(확인 후)를 자동으로 처리합니다."""
    mode = "[bold yellow]DRY RUN 모드[/bold yellow]" if dry_run else "[bold green]LIVE 모드[/bold green]"

    console.print(Panel.fit(
        f"[bold blue]Gmail Auto Cleaner[/bold blue]  {mode}\n"
        "[dim]받은편지함을 자동으로 스캔하고, 라벨 적용 → 아카이브 → 삭제(확인 후) 순서로 처리합니다.[/dim]",
        border_style="blue",
    ))

    if dry_run:
        console.print(
            "[bold yellow]DRY RUN: 실제 삭제·아카이브·라벨 작업은 실행되지 않습니다.[/bold yellow]"
        )

    try:
        with console.status("Gmail에 연결 중..."):
            service = get_gmail_service()
        console.print("[green]Gmail 연결 완료.[/green]")
    except FileNotFoundError as e:
        console.print(f"[bold red]오류:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]인증 실패:[/bold red] {e}")
        sys.exit(1)

    try:
        run_auto_pipeline(service, dry_run)
    except HttpError as e:
        console.print(f"[bold red]Gmail API 오류:[/bold red] {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]중단되었습니다.[/dim]")


if __name__ == "__main__":
    main()
