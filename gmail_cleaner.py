"""Gmail Cleaner - Interactive tool to clean up your Gmail inbox."""

import sys
import time
from typing import Optional

import click
from googleapiclient.errors import HttpError
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich import box

from auth import get_gmail_service

console = Console()

MAX_RESULTS_PER_PAGE = 500
BATCH_SIZE = 50  # Gmail API batch delete limit


# ---------------------------------------------------------------------------
# Gmail API helpers
# ---------------------------------------------------------------------------

def fetch_message_ids(service, query: str, max_results: Optional[int] = None) -> list[str]:
    """Return all message IDs matching a Gmail search query."""
    ids = []
    page_token = None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Searching emails...", total=None)

        while True:
            kwargs = {
                "userId": "me",
                "q": query,
                "maxResults": MAX_RESULTS_PER_PAGE,
            }
            if page_token:
                kwargs["pageToken"] = page_token

            result = service.users().messages().list(**kwargs).execute()
            messages = result.get("messages", [])
            ids.extend(m["id"] for m in messages)

            progress.update(task, description=f"Found {len(ids)} emails...")

            if max_results and len(ids) >= max_results:
                ids = ids[:max_results]
                break

            page_token = result.get("nextPageToken")
            if not page_token:
                break

    return ids


def get_message_snippet(service, msg_id: str) -> dict:
    """Fetch sender, subject, and date for a message."""
    msg = service.users().messages().get(
        userId="me", id=msg_id, format="metadata",
        metadataHeaders=["From", "Subject", "Date"]
    ).execute()

    headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": msg_id,
        "from": headers.get("From", "(unknown)"),
        "subject": headers.get("Subject", "(no subject)"),
        "date": headers.get("Date", ""),
    }


def batch_delete(service, msg_ids: list[str], dry_run: bool = False) -> int:
    """Delete messages in batches. Returns count of deleted messages."""
    if dry_run:
        console.print(f"[yellow][DRY RUN] Would delete {len(msg_ids)} emails.[/yellow]")
        return 0

    deleted = 0
    batches = [msg_ids[i:i + BATCH_SIZE] for i in range(0, len(msg_ids), BATCH_SIZE)]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Deleting...", total=len(batches))

        for batch in batches:
            service.users().messages().batchDelete(
                userId="me",
                body={"ids": batch},
            ).execute()
            deleted += len(batch)
            progress.advance(task)
            time.sleep(0.1)  # avoid rate limiting

    return deleted


def batch_archive(service, msg_ids: list[str], dry_run: bool = False) -> int:
    """Archive (remove INBOX label) messages in batches."""
    if dry_run:
        console.print(f"[yellow][DRY RUN] Would archive {len(msg_ids)} emails.[/yellow]")
        return 0

    archived = 0
    batches = [msg_ids[i:i + BATCH_SIZE] for i in range(0, len(msg_ids), BATCH_SIZE)]

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Archiving...", total=len(batches))

        for batch in batches:
            service.users().messages().batchModify(
                userId="me",
                body={
                    "ids": batch,
                    "removeLabelIds": ["INBOX"],
                },
            ).execute()
            archived += len(batch)
            progress.advance(task)
            time.sleep(0.1)

    return archived


def show_preview(service, msg_ids: list[str], limit: int = 10):
    """Print a preview table of the first N messages."""
    preview_ids = msg_ids[:limit]
    table = Table(box=box.ROUNDED, show_lines=True)
    table.add_column("From", style="cyan", max_width=35, no_wrap=True)
    table.add_column("Subject", style="white", max_width=50, no_wrap=True)
    table.add_column("Date", style="dim", max_width=30)

    for mid in preview_ids:
        info = get_message_snippet(service, mid)
        table.add_row(info["from"], info["subject"], info["date"])

    console.print(table)
    if len(msg_ids) > limit:
        console.print(f"[dim]... and {len(msg_ids) - limit} more.[/dim]")


# ---------------------------------------------------------------------------
# Individual feature commands
# ---------------------------------------------------------------------------

def cmd_delete_by_sender(service, dry_run: bool):
    """Delete all emails from a specific sender."""
    sender = Prompt.ask("[bold]Enter sender email or domain[/bold] (e.g. newsletter@example.com)")
    if not sender.strip():
        return

    query = f"from:{sender.strip()}"
    ids = fetch_message_ids(service, query)
    if not ids:
        console.print("[green]No emails found from that sender.[/green]")
        return

    console.print(f"\n[bold]Found {len(ids)} emails[/bold] from [cyan]{sender}[/cyan]\n")
    show_preview(service, ids)

    if Confirm.ask(f"\nDelete all [bold red]{len(ids)}[/bold red] emails?"):
        deleted = batch_delete(service, ids, dry_run)
        if not dry_run:
            console.print(f"[green]Deleted {deleted} emails.[/green]")


def cmd_delete_by_keyword(service, dry_run: bool):
    """Delete emails matching a search keyword."""
    keyword = Prompt.ask("[bold]Enter search keyword or Gmail query[/bold] (e.g. 'unsubscribe', 'subject:promo')")
    if not keyword.strip():
        return

    ids = fetch_message_ids(service, keyword.strip())
    if not ids:
        console.print("[green]No emails found.[/green]")
        return

    console.print(f"\n[bold]Found {len(ids)} emails[/bold] matching [cyan]{keyword}[/cyan]\n")
    show_preview(service, ids)

    if Confirm.ask(f"\nDelete all [bold red]{len(ids)}[/bold red] emails?"):
        deleted = batch_delete(service, ids, dry_run)
        if not dry_run:
            console.print(f"[green]Deleted {deleted} emails.[/green]")


def cmd_delete_old_emails(service, dry_run: bool):
    """Delete emails older than N days."""
    days = Prompt.ask("[bold]Delete emails older than how many days?[/bold]", default="365")
    try:
        days_int = int(days)
    except ValueError:
        console.print("[red]Invalid number.[/red]")
        return

    query = f"older_than:{days_int}d"
    ids = fetch_message_ids(service, query)
    if not ids:
        console.print(f"[green]No emails older than {days_int} days found.[/green]")
        return

    console.print(f"\n[bold]Found {len(ids)} emails[/bold] older than [cyan]{days_int} days[/cyan]\n")
    show_preview(service, ids)

    if Confirm.ask(f"\nDelete all [bold red]{len(ids)}[/bold red] old emails?"):
        deleted = batch_delete(service, ids, dry_run)
        if not dry_run:
            console.print(f"[green]Deleted {deleted} emails.[/green]")


def cmd_delete_promotions(service, dry_run: bool):
    """Delete all emails in the Promotions category."""
    query = "category:promotions"
    ids = fetch_message_ids(service, query)
    if not ids:
        console.print("[green]No promotion emails found.[/green]")
        return

    console.print(f"\n[bold]Found {len(ids)} promotion emails[/bold]\n")
    show_preview(service, ids)

    if Confirm.ask(f"\nDelete all [bold red]{len(ids)}[/bold red] promotion emails?"):
        deleted = batch_delete(service, ids, dry_run)
        if not dry_run:
            console.print(f"[green]Deleted {deleted} promotion emails.[/green]")


def cmd_delete_social(service, dry_run: bool):
    """Delete all emails in the Social category."""
    query = "category:social"
    ids = fetch_message_ids(service, query)
    if not ids:
        console.print("[green]No social emails found.[/green]")
        return

    console.print(f"\n[bold]Found {len(ids)} social emails[/bold]\n")
    show_preview(service, ids)

    if Confirm.ask(f"\nDelete all [bold red]{len(ids)}[/bold red] social emails?"):
        deleted = batch_delete(service, ids, dry_run)
        if not dry_run:
            console.print(f"[green]Deleted {deleted} social emails.[/green]")


def cmd_archive_read(service, dry_run: bool):
    """Archive all read emails in inbox."""
    query = "in:inbox is:read"
    ids = fetch_message_ids(service, query)
    if not ids:
        console.print("[green]No read emails in inbox.[/green]")
        return

    console.print(f"\n[bold]Found {len(ids)} read emails[/bold] in inbox\n")
    show_preview(service, ids)

    if Confirm.ask(f"\nArchive all [bold yellow]{len(ids)}[/bold yellow] read emails?"):
        archived = batch_archive(service, ids, dry_run)
        if not dry_run:
            console.print(f"[green]Archived {archived} emails.[/green]")


def cmd_stats(service):
    """Show inbox statistics."""
    console.print("\n[bold]Fetching inbox statistics...[/bold]")

    queries = [
        ("Total inbox", "in:inbox"),
        ("Unread", "in:inbox is:unread"),
        ("Read", "in:inbox is:read"),
        ("Promotions", "category:promotions"),
        ("Social", "category:social"),
        ("Updates", "category:updates"),
        ("Forums", "category:forums"),
        ("Older than 1 year", "older_than:365d"),
        ("Has attachment", "has:attachment"),
    ]

    table = Table(title="Inbox Statistics", box=box.ROUNDED)
    table.add_column("Category", style="cyan")
    table.add_column("Count", style="bold white", justify="right")

    for label, query in queries:
        ids = fetch_message_ids(service, query, max_results=5000)
        count_str = str(len(ids)) if len(ids) < 5000 else "5000+"
        table.add_row(label, count_str)

    console.print(table)


def cmd_top_senders(service):
    """Show top senders by email count."""
    console.print("\n[bold]Analyzing top senders (scanning up to 1000 emails)...[/bold]")

    ids = fetch_message_ids(service, "in:inbox", max_results=1000)
    if not ids:
        console.print("[green]Inbox is empty.[/green]")
        return

    sender_counts: dict[str, int] = {}

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Reading headers...", total=len(ids))
        for mid in ids:
            try:
                info = get_message_snippet(service, mid)
                sender = info["from"]
                sender_counts[sender] = sender_counts.get(sender, 0) + 1
            except HttpError:
                pass
            progress.advance(task)

    sorted_senders = sorted(sender_counts.items(), key=lambda x: x[1], reverse=True)

    table = Table(title="Top 20 Senders", box=box.ROUNDED, show_lines=True)
    table.add_column("Sender", style="cyan", max_width=60, no_wrap=True)
    table.add_column("Count", style="bold white", justify="right")

    for sender, count in sorted_senders[:20]:
        table.add_row(sender, str(count))

    console.print(table)


# ---------------------------------------------------------------------------
# Main interactive menu
# ---------------------------------------------------------------------------

MENU_OPTIONS = [
    ("1", "Delete emails from a specific sender"),
    ("2", "Delete emails by keyword / query"),
    ("3", "Delete emails older than N days"),
    ("4", "Delete all Promotion emails"),
    ("5", "Delete all Social emails"),
    ("6", "Archive all read inbox emails"),
    ("7", "Show inbox statistics"),
    ("8", "Show top senders"),
    ("q", "Quit"),
]


def print_menu(dry_run: bool):
    mode = "[bold yellow]DRY RUN MODE[/bold yellow]" if dry_run else "[bold green]LIVE MODE[/bold green]"
    table = Table(box=box.ROUNDED, show_header=False, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=4)
    table.add_column("Action", style="white")

    for key, description in MENU_OPTIONS:
        table.add_row(key, description)

    console.print(
        Panel(
            table,
            title=f"[bold]Gmail Cleaner[/bold]  {mode}",
            border_style="blue",
        )
    )


@click.command()
@click.option("--dry-run", is_flag=True, default=False, help="Preview actions without deleting anything.")
def main(dry_run: bool):
    """Interactive Gmail cleanup tool."""
    console.print(Panel.fit(
        "[bold blue]Gmail Cleaner[/bold blue]\n"
        "[dim]Authenticate once, then manage your inbox interactively.[/dim]",
        border_style="blue",
    ))

    if dry_run:
        console.print("[bold yellow]Running in DRY RUN mode — no emails will be modified.[/bold yellow]\n")

    try:
        with console.status("Connecting to Gmail..."):
            service = get_gmail_service()
        console.print("[green]Connected to Gmail.[/green]\n")
    except FileNotFoundError as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Authentication failed:[/bold red] {e}")
        sys.exit(1)

    while True:
        print_menu(dry_run)
        choice = Prompt.ask("[bold]Choose an option[/bold]", default="q").strip().lower()

        console.print()

        try:
            if choice == "1":
                cmd_delete_by_sender(service, dry_run)
            elif choice == "2":
                cmd_delete_by_keyword(service, dry_run)
            elif choice == "3":
                cmd_delete_old_emails(service, dry_run)
            elif choice == "4":
                cmd_delete_promotions(service, dry_run)
            elif choice == "5":
                cmd_delete_social(service, dry_run)
            elif choice == "6":
                cmd_archive_read(service, dry_run)
            elif choice == "7":
                cmd_stats(service)
            elif choice == "8":
                cmd_top_senders(service)
            elif choice == "q":
                console.print("[dim]Goodbye![/dim]")
                break
            else:
                console.print("[red]Invalid option.[/red]")
        except HttpError as e:
            console.print(f"[bold red]Gmail API error:[/bold red] {e}")
        except KeyboardInterrupt:
            console.print("\n[dim]Interrupted.[/dim]")

        console.print()


if __name__ == "__main__":
    main()
