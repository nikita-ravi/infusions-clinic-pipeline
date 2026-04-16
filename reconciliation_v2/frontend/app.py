"""Streamlit dashboard for reconciliation results."""

import json
from pathlib import Path

import streamlit as st

# Page config
st.set_page_config(
    page_title="Payer Route Reconciliation",
    page_icon="🏥",
    layout="wide",
)

# Find output directory
OUTPUT_DIR = Path(__file__).parent.parent.parent / "output_v2"


def load_reconciliation_data(payer_key: str) -> dict | None:
    """Load reconciliation JSON for a payer."""
    json_path = OUTPUT_DIR / f"{payer_key}_reconciled.json"
    if json_path.exists():
        return json.loads(json_path.read_text())
    return None


def get_available_payers() -> list[str]:
    """Get list of payers with reconciliation data."""
    if not OUTPUT_DIR.exists():
        return []
    return [
        f.stem.replace("_reconciled", "")
        for f in OUTPUT_DIR.glob("*_reconciled.json")
    ]


def render_tldr(data: dict):
    """Render the TL;DR section."""
    summary = data.get("executive_summary")
    if summary:
        st.markdown("### 📋 TL;DR")
        st.info(summary)
    else:
        st.markdown("### 📋 TL;DR")
        st.warning("No executive summary available (LLM not enabled during reconciliation)")


def render_best_route(data: dict):
    """Render the best route section."""
    best_route = data.get("best_route", {})

    st.markdown("### 🎯 Best Route (Actionable)")

    col1, col2 = st.columns(2)

    with col1:
        # Submission method
        submission = best_route.get("submission", {})
        if submission:
            st.markdown("#### Submission Method")
            preferred = submission.get("preferred_method", "unknown").upper()
            st.success(f"**Preferred:** {preferred}")

            if submission.get("preferred_url"):
                st.markdown(f"🔗 URL: `{submission['preferred_url']}`")

            if submission.get("fallback_method"):
                st.warning(f"**Fallback:** {submission['fallback_method'].upper()}")
                if submission.get("fallback_fax"):
                    st.markdown(f"📠 Fax: `{submission['fallback_fax']}`")

            if submission.get("do_not_use"):
                st.error("**Do NOT Use:**")
                for item in submission["do_not_use"]:
                    st.markdown(f"- ~~{item}~~")

        # Contact info
        contact = best_route.get("contact", {})
        if contact:
            st.markdown("#### Contact Information")
            if contact.get("status_phone"):
                st.markdown(f"📞 Status: `{contact['status_phone']}`")
            if contact.get("appeal_fax"):
                st.markdown(f"📠 Appeal Fax: `{contact['appeal_fax']}`")
            if contact.get("appeal_deadline_days"):
                st.markdown(f"⏰ Appeal Deadline: **{contact['appeal_deadline_days']} days**")

    with col2:
        # Turnaround times
        turnaround = best_route.get("turnaround", {})
        if turnaround:
            st.markdown("#### Turnaround Times")
            for method, time in turnaround.items():
                method_label = method.replace("_", " ").title()
                st.markdown(f"- **{method_label}:** {time}")

        # Required documents
        docs = best_route.get("required_documents", [])
        if docs:
            st.markdown("#### Required Documents")
            for doc in docs:
                st.markdown(f"- 📄 {doc}")

    # Drug requirements - ALL DRUGS
    all_drug_req = best_route.get("all_drug_requirements", {})
    if all_drug_req:
        st.markdown("#### 💊 Drug-Specific Requirements")

        # Get focus drug from data
        focus_drug = data.get("summary", {}).get("focus_drug")

        # Create tabs for each drug
        drug_names = sorted(all_drug_req.keys(), key=lambda d: (d != focus_drug, d))
        tabs = st.tabs([f"{'⭐ ' if d == focus_drug else ''}{d}" for d in drug_names])

        for tab, drug_name in zip(tabs, drug_names):
            with tab:
                drug_req = all_drug_req[drug_name]
                req_cols = st.columns(3)
                col_idx = 0
                for key, value in drug_req.items():
                    if key == "drug_name" or key == "notes":
                        continue
                    with req_cols[col_idx % 3]:
                        label = key.replace("_", " ").title()
                        if isinstance(value, bool):
                            if value:
                                st.markdown(f"✅ {label}")
                            else:
                                st.markdown(f"❌ {label}")
                        else:
                            st.markdown(f"**{label}:** {value}")
                    col_idx += 1

                if drug_req.get("notes"):
                    st.markdown("**Notes:**")
                    for note in drug_req["notes"]:
                        st.caption(f"> {note}")

    # Restrictions
    restrictions = best_route.get("restrictions", [])
    if restrictions:
        st.markdown("#### ⚠️ Restrictions & Warnings")
        for r in restrictions:
            st.warning(r)


def render_conflicts(data: dict):
    """Render conflicts section."""
    fields = data.get("fields", {})
    conflicts = {k: v for k, v in fields.items() if v.get("has_conflicts")}

    if not conflicts:
        st.success("No conflicts detected!")
        return

    st.markdown(f"### ⚠️ Conflicts ({len(conflicts)} fields)")

    for field_name, field_data in conflicts.items():
        with st.expander(f"🔸 {field_name.replace('_', ' ').title()}", expanded=False):
            st.markdown(f"**Selected Value:** `{field_data.get('value')}`")
            st.markdown(f"**Confidence:** {field_data.get('confidence', 0):.2%}")
            st.markdown(f"**Source:** {field_data.get('source_id')} ({field_data.get('source_type')})")

            all_values = field_data.get("all_values", {})
            if all_values:
                st.markdown("**All Values:**")
                for source_id, value in all_values.items():
                    superseded = " _(superseded)_" if source_id in field_data.get("superseded_values", []) else ""
                    selected = " ✓" if source_id == field_data.get("source_id") else ""
                    st.markdown(f"- `{source_id}`: {value}{superseded}{selected}")

            if field_data.get("supersession_reasons"):
                st.markdown("**Supersession:**")
                for reason in field_data["supersession_reasons"]:
                    st.caption(reason)


def render_summary_stats(data: dict):
    """Render summary statistics."""
    summary = data.get("summary", {})

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Fields Discovered", summary.get("total_fields_discovered", 0))
    with col2:
        st.metric("Fields Output", summary.get("total_fields_output", 0))
    with col3:
        st.metric("Conflicts", summary.get("conflicts_detected", 0))
    with col4:
        st.metric("Raw Text Validated", summary.get("fields_validated_against_raw", 0))


def render_raw_json(data: dict):
    """Render raw JSON for debugging."""
    st.json(data)


def main():
    st.title("🏥 Payer Route Reconciliation Dashboard")

    # Sidebar for payer selection
    payers = get_available_payers()

    if not payers:
        st.error(
            "No reconciliation data found. Run the pipeline first:\n\n"
            "```bash\n"
            "python -m reconciliation_v2.main\n"
            "```"
        )
        return

    # Payer selector
    selected_payer = st.sidebar.selectbox(
        "Select Payer",
        payers,
        format_func=lambda x: x.replace("_", " ").title()
    )

    # Load data
    data = load_reconciliation_data(selected_payer)

    if not data:
        st.error(f"Could not load data for {selected_payer}")
        return

    # Header
    st.markdown(f"## {data.get('payer', selected_payer)}")

    # Payer warnings
    warnings = data.get("payer_warnings", [])
    if warnings:
        for warning in warnings:
            st.error(f"⚠️ {warning}")

    # Summary stats
    render_summary_stats(data)

    st.divider()

    # TL;DR
    render_tldr(data)

    st.divider()

    # Best Route
    render_best_route(data)

    st.divider()

    # Conflicts
    render_conflicts(data)

    # Raw JSON (collapsible)
    with st.expander("🔧 Raw JSON Data", expanded=False):
        render_raw_json(data)


if __name__ == "__main__":
    main()
