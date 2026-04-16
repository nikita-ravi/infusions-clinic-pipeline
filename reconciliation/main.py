"""Main CLI for reconciliation pipeline."""

import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from reconciliation.models.source import PayerData, SourceRecord
from reconciliation.pipeline.reasoning import generate_reasoning
from reconciliation.pipeline.reconcile import reconcile_payer
from reconciliation.reports.json_report import generate_json_report
from reconciliation.reports.markdown_report import generate_markdown_report

console = Console()


def load_payer_data(data_path: Path) -> dict[str, PayerData]:
    """Load payer data from extracted_route_data.json."""
    with open(data_path) as f:
        raw_data = json.load(f)

    payer_data = {}

    for payer_key, payer_info in raw_data.items():
        sources = []
        for source_dict in payer_info["sources"]:
            # Parse dates
            source_date = datetime.strptime(source_dict["source_date"], "%Y-%m-%d").date()
            retrieved_date = datetime.strptime(
                source_dict["retrieved_date"], "%Y-%m-%d"
            ).date()

            sources.append(
                SourceRecord(
                    source_id=source_dict["source_id"],
                    source_type=source_dict["source_type"],
                    source_name=source_dict["source_name"],
                    source_date=source_date,
                    retrieved_date=retrieved_date,
                    data=source_dict["data"],
                )
            )

        payer_data[payer_key] = PayerData(
            payer=payer_info["payer"],
            sources=sources,
        )

    return payer_data


def run_reconciliation(
    data_path: Path,
    output_dir: Path,
    focus_drug: str = "Remicade",
    add_reasoning: bool = False,
    api_key: str | None = None,
) -> None:
    """Run reconciliation pipeline for all payers."""
    console.print("\n[bold cyan]Payer Route Reconciliation Pipeline[/bold cyan]")
    console.print(f"[dim]Focus drug: {focus_drug}[/dim]\n")

    # Load data
    console.print("[yellow]Loading payer data...[/yellow]")
    payer_data = load_payer_data(data_path)
    console.print(f"[green]✓[/green] Loaded {len(payer_data)} payers\n")

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Reconcile each payer
    results = {}

    for payer_key, payer in payer_data.items():
        console.print(f"[bold]Processing {payer.payer}...[/bold]")

        # Run reconciliation
        reconciliation = reconcile_payer(payer, focus_drug=focus_drug)

        # Add LLM reasoning if requested
        if add_reasoning:
            console.print("  [yellow]Generating LLM reasoning...[/yellow]")
            reasoning_count = 0
            for field_name, field_rec in reconciliation.fields.items():
                if field_rec.value is not None:
                    reasoning = generate_reasoning(field_rec, payer.payer, api_key=api_key)
                    field_rec.reasoning = reasoning
                    reasoning_count += 1
            console.print(f"  [green]✓[/green] Added reasoning for {reasoning_count} fields")

        results[payer_key] = reconciliation

        # Generate reports
        json_path = output_dir / f"{payer_key}_reconciled.json"
        md_path = output_dir / f"{payer_key}_report.md"

        generate_json_report(reconciliation, json_path)
        generate_markdown_report(reconciliation, md_path)

        console.print(f"  [green]✓[/green] JSON: {json_path}")
        console.print(f"  [green]✓[/green] Markdown: {md_path}")

        # Print summary table
        _print_summary_table(reconciliation)

        console.print()

    console.print("[bold green]✓ Pipeline complete![/bold green]\n")


def _print_summary_table(reconciliation):
    """Print a summary table for a payer."""
    table = Table(title=f"{reconciliation.payer} Summary", show_header=True, header_style="bold")

    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="magenta")

    summary = reconciliation.summary

    table.add_row("Total Sources", str(summary.get("total_sources", 0)))
    table.add_row("Fields Reconciled", str(summary.get("fields_reconciled", 0)))
    table.add_row("Conflicts Detected", str(summary.get("conflicts_detected", 0)))
    table.add_row(
        "High Confidence Fields (≥0.8)",
        str(summary.get("high_confidence_fields", 0)),
    )
    table.add_row(
        "Low Confidence Fields (<0.5)",
        str(summary.get("low_confidence_fields", 0)),
    )

    console.print(table)


def main():
    """Main entry point."""
    import sys

    data_path = Path("payer_sources/extracted_route_data.json")
    output_dir = Path("output")

    # Check for --with-reasoning flag
    add_reasoning = "--with-reasoning" in sys.argv
    api_key = None

    # Check for --api-key argument
    if "--api-key" in sys.argv:
        try:
            key_index = sys.argv.index("--api-key")
            api_key = sys.argv[key_index + 1]
        except (ValueError, IndexError):
            console.print("[red]Error: --api-key requires a value[/red]")
            return

    if not data_path.exists():
        console.print(f"[red]Error: {data_path} not found[/red]")
        return

    run_reconciliation(
        data_path=data_path,
        output_dir=output_dir,
        focus_drug="Remicade",
        add_reasoning=add_reasoning,
        api_key=api_key,
    )


if __name__ == "__main__":
    main()
