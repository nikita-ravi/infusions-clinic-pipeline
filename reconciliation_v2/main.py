"""Main CLI for reconciliation pipeline v2."""

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

from reconciliation_v2.pipeline.reconcile import run_reconciliation
from reconciliation_v2.reports.json_report import generate_json_report
from reconciliation_v2.reports.markdown_report import generate_markdown_report

console = Console()


def main():
    """Main entry point."""
    data_path = Path("payer_sources/extracted_route_data.json")
    output_dir = Path("output_v2")

    # Parse arguments
    payer_keys = None
    drug_override = None

    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--payer":
            payer_keys = args[i + 1].split(",")
            i += 2
        elif args[i] == "--drug":
            drug_override = args[i + 1]
            i += 2
        else:
            i += 1

    if not data_path.exists():
        console.print(f"[red]Error: {data_path} not found[/red]")
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)

    console.print("\n[bold cyan]Payer Route Reconciliation Pipeline v2[/bold cyan]")
    console.print("[dim]Schema-driven, pattern-based reconciliation[/dim]\n")

    # Run reconciliation
    results = run_reconciliation(
        data_path=data_path,
        payer_keys=payer_keys,
        drug_override=drug_override,
    )

    # Generate reports
    for payer_key, reconciliation in results.items():
        console.print(f"[bold]Processing {reconciliation.payer}...[/bold]")

        # Generate reports
        json_path = output_dir / f"{payer_key}_reconciled.json"
        md_path = output_dir / f"{payer_key}_report.md"

        generate_json_report(reconciliation, json_path)
        generate_markdown_report(reconciliation, md_path)

        console.print(f"  [green]✓[/green] JSON: {json_path}")
        console.print(f"  [green]✓[/green] Markdown: {md_path}")

        # Print summary table
        _print_summary_table(reconciliation)

        # Print payer warnings
        if reconciliation.payer_warnings:
            console.print()
            for warning in reconciliation.payer_warnings:
                console.print(f"  [yellow]⚠️ {warning}[/yellow]")

        console.print()

    console.print("[bold green]✓ Pipeline complete![/bold green]")
    console.print(f"\nOutput directory: {output_dir.absolute()}")

    return 0


def _print_summary_table(reconciliation):
    """Print a summary table for a payer."""
    table = Table(title=f"{reconciliation.payer} Summary", show_header=True, header_style="bold")

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    table.add_row("Focus Drug", reconciliation.focus_drug or "N/A")
    table.add_row("Fields Discovered", str(reconciliation.total_fields_discovered))
    table.add_row("Fields Output", str(reconciliation.total_fields_output))
    table.add_row("Conflicts Detected", str(reconciliation.conflicts_detected))

    console.print(table)


if __name__ == "__main__":
    sys.exit(main())
