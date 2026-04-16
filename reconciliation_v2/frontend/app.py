"""Streamlit dashboard for PA route reconciliation."""

import json
from pathlib import Path

import streamlit as st

# Page config
st.set_page_config(
    page_title="PA Route Reconciliation",
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


def load_all_payer_data() -> dict[str, dict]:
    """Load all payer data."""
    data = {}
    for f in OUTPUT_DIR.glob("*_reconciled.json"):
        payer_key = f.stem.replace("_reconciled", "")
        data[payer_key] = json.loads(f.read_text())
    return data


def get_available_payers() -> list[str]:
    """Get list of payers with reconciliation data."""
    if not OUTPUT_DIR.exists():
        return []
    return sorted([
        f.stem.replace("_reconciled", "")
        for f in OUTPUT_DIR.glob("*_reconciled.json")
    ])


def confidence_color(conf: float) -> str:
    """Return color based on confidence score."""
    if conf >= 0.85:
        return "green"
    elif conf >= 0.70:
        return "orange"
    else:
        return "red"


def render_confidence_badge(conf: float, label: str = ""):
    """Render a colored confidence badge."""
    color = confidence_color(conf)
    if color == "green":
        st.success(f"{label}{conf:.0%} confidence")
    elif color == "orange":
        st.warning(f"{label}{conf:.0%} confidence")
    else:
        st.error(f"{label}{conf:.0%} confidence")


# =============================================================================
# PAGE 1: PAYER ROUTE DASHBOARD
# =============================================================================
def render_payer_dashboard(data: dict):
    """Render the main payer route dashboard."""

    # Payer warnings banner at top
    warnings = data.get("payer_warnings", [])
    if warnings:
        for warning in warnings:
            st.error(f"⚠️ **PAYER ALERT:** {warning}")
        st.divider()

    # Summary metrics row
    summary = data.get("summary", {})
    cols = st.columns(4)
    with cols[0]:
        st.metric("Focus Drug", summary.get("focus_drug", "N/A"))
    with cols[1]:
        st.metric("Fields Reconciled", summary.get("total_fields_output", 0))
    with cols[2]:
        conflicts = summary.get("conflicts_detected", 0)
        st.metric("Conflicts", conflicts, delta=None if conflicts == 0 else f"{conflicts} fields", delta_color="inverse")
    with cols[3]:
        st.metric("Raw Text Validated", summary.get("fields_validated_against_raw", 0))

    st.divider()

    # BEST ROUTE CARD - The main actionable output
    st.markdown("## 🎯 Best Route")
    best_route = data.get("best_route", {})

    col1, col2 = st.columns(2)

    with col1:
        # Submission Method Card
        st.markdown("### Submission Method")
        submission = best_route.get("submission", {})

        preferred = submission.get("preferred_method", "unknown").upper()
        if preferred == "PORTAL":
            st.success(f"**Preferred: {preferred}**")
            if submission.get("preferred_url"):
                st.code(submission["preferred_url"], language=None)
        else:
            st.info(f"**Preferred: {preferred}**")

        if submission.get("fallback_method"):
            st.warning(f"**Fallback: {submission['fallback_method'].upper()}**")
            if submission.get("fallback_fax"):
                st.code(submission["fallback_fax"], language=None)

        # DO NOT USE - Critical warning
        if submission.get("do_not_use"):
            st.error("**❌ DO NOT USE (Deprecated):**")
            for item in submission["do_not_use"]:
                st.markdown(f"~~{item}~~")

        st.markdown("---")

        # Contact Information
        st.markdown("### Contact Information")
        contact = best_route.get("contact", {})
        if contact.get("status_phone"):
            st.markdown(f"**📞 Status Phone:** `{contact['status_phone']}`")
        if contact.get("appeal_fax"):
            st.markdown(f"**📠 Appeal Fax:** `{contact['appeal_fax']}`")
        if contact.get("appeal_phone"):
            st.markdown(f"**📞 Appeal Phone:** `{contact['appeal_phone']}`")
        if contact.get("appeal_deadline_days"):
            st.markdown(f"**⏰ Appeal Deadline:** {contact['appeal_deadline_days']} days")

    with col2:
        # Turnaround Times
        st.markdown("### Turnaround Times")
        turnaround = best_route.get("turnaround", {})
        if turnaround:
            for method, time in turnaround.items():
                method_label = method.replace("_", " ").title()
                if isinstance(time, dict):
                    time_str = f"{time.get('min', '?')}-{time.get('max', '?')} days"
                else:
                    time_str = str(time)
                st.markdown(f"- **{method_label}:** {time_str}")
        else:
            st.caption("No turnaround data available")

        st.markdown("---")

        # Required Documents
        st.markdown("### Required Documents")
        docs = best_route.get("required_documents", [])
        if docs:
            for doc in docs:
                st.checkbox(doc, value=False, key=f"doc_{hash(doc)}")
        else:
            st.caption("No specific documents listed")

    st.divider()

    # DRUG-SPECIFIC REQUIREMENTS
    st.markdown("## 💊 Drug-Specific Requirements")

    all_drug_req = best_route.get("all_drug_requirements", {})
    focus_drug = summary.get("focus_drug")

    if all_drug_req:
        # Sort with focus drug first
        drug_names = sorted(all_drug_req.keys(), key=lambda d: (d != focus_drug, d))
        tabs = st.tabs([f"{'⭐ ' if d == focus_drug else ''}{d}" for d in drug_names])

        for tab, drug_name in zip(tabs, drug_names):
            with tab:
                drug_req = all_drug_req[drug_name]

                # Key requirements in columns
                req_col1, req_col2, req_col3 = st.columns(3)

                with req_col1:
                    st.markdown("**Authorization**")
                    auth_initial = drug_req.get("auth_period_initial_months") or drug_req.get("auth_period_months")
                    auth_renewal = drug_req.get("auth_period_renewal_months")
                    if auth_initial:
                        st.markdown(f"- Initial: **{auth_initial} months**")
                    if auth_renewal and auth_renewal != auth_initial:
                        st.markdown(f"- Renewal: **{auth_renewal} months**")
                    if not auth_initial and not auth_renewal:
                        st.caption("Not specified")

                with req_col2:
                    st.markdown("**Requirements**")
                    if drug_req.get("step_therapy_required"):
                        st.markdown("✅ Step therapy required")
                    if drug_req.get("prior_treatment_failure_required"):
                        st.markdown("✅ Prior treatment failure")
                    if drug_req.get("specialist_required"):
                        st.markdown("✅ Specialist required")
                    biosim = drug_req.get("biosimilar_requirement")
                    if biosim and biosim != "not_stated":
                        st.markdown(f"💊 Biosimilar: **{biosim}**")

                with req_col3:
                    st.markdown("**Testing & Documentation**")
                    testing = drug_req.get("specific_testing", [])
                    if testing:
                        for test in testing:
                            st.markdown(f"🔬 {test}")
                    doc_req = drug_req.get("documentation_requirements", [])
                    if doc_req:
                        for doc in doc_req:
                            st.markdown(f"📄 {doc}")
                    if not testing and not doc_req:
                        st.caption("Standard documentation")

                # Notes
                notes = drug_req.get("notes", [])
                if notes:
                    with st.expander("📝 Additional Notes"):
                        for note in notes:
                            st.caption(f"• {note}")
    else:
        st.info("No drug-specific requirements extracted")

    st.divider()

    # CONFLICTS PANEL (Collapsible)
    fields = data.get("fields", {})
    conflicts = {k: v for k, v in fields.items() if v.get("has_conflicts")}

    with st.expander(f"⚠️ Conflicts & Resolution ({len(conflicts)} fields)", expanded=False):
        if not conflicts:
            st.success("No conflicts detected - all sources agree!")
        else:
            for field_name, field_data in conflicts.items():
                st.markdown(f"#### {field_name.replace('_', ' ').title()}")

                conf = field_data.get("confidence", 0)
                color = confidence_color(conf)

                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Selected:** `{field_data.get('value')}`")
                    st.markdown(f"**Source:** {field_data.get('source_id')} ({field_data.get('source_type')})")
                with col2:
                    render_confidence_badge(conf)

                # Show all values
                all_values = field_data.get("all_values", {})
                if all_values:
                    st.markdown("**All source values:**")
                    for source_id, value in all_values.items():
                        superseded = "~~" if source_id in field_data.get("superseded_values", []) else ""
                        selected = " ✓" if source_id == field_data.get("source_id") else ""
                        st.markdown(f"- `{source_id}`: {superseded}{value}{superseded}{selected}")

                # Supersession reasons
                if field_data.get("supersession_reasons"):
                    st.caption("Supersession: " + "; ".join(field_data["supersession_reasons"][:2]))

                st.markdown("---")


# =============================================================================
# PAGE 2: DECISION AUDIT TRAIL
# =============================================================================
def render_audit_trail(data: dict):
    """Render the decision audit trail page."""

    st.markdown("## 🔍 Decision Audit Trail")
    st.caption("Select a field to see the full reconciliation breakdown")

    fields = data.get("fields", {})
    raw_validations = data.get("raw_text_validations", {})

    # Field selector
    field_names = sorted(fields.keys())
    selected_field = st.selectbox(
        "Select Field",
        field_names,
        format_func=lambda x: f"{'⚠️ ' if fields[x].get('has_conflicts') else '✓ '}{x.replace('_', ' ').title()}"
    )

    if selected_field:
        field_data = fields[selected_field]

        st.divider()

        # Header with confidence
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {selected_field.replace('_', ' ').title()}")
            st.markdown(f"**Final Value:** `{field_data.get('value')}`")
        with col2:
            render_confidence_badge(field_data.get("confidence", 0))

        st.divider()

        # Source breakdown
        st.markdown("#### 📊 Source Values")

        raw_fields = data.get("raw_fields", {}).get(selected_field, {})
        source_values = raw_fields.get("values", [])

        if source_values:
            for sv in source_values:
                source_id = sv.get("source_id", "")
                is_selected = source_id == field_data.get("source_id")
                is_superseded = source_id in field_data.get("superseded_values", [])

                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                with col1:
                    marker = "✓ " if is_selected else ("~~" if is_superseded else "")
                    end_marker = "~~" if is_superseded else ""
                    st.markdown(f"**{marker}{sv.get('source_id')}{end_marker}**")
                with col2:
                    st.caption(sv.get("source_type", "").replace("_", " ").title())
                with col3:
                    st.caption(sv.get("source_date", ""))
                with col4:
                    if is_superseded:
                        st.caption("❌ Superseded")
                    elif is_selected:
                        st.caption("✅ Selected")

                st.markdown(f"Value: `{sv.get('value')}`")
                st.markdown("---")

        # Decision path
        st.markdown("#### 🧮 Scoring Breakdown")
        decision_path = field_data.get("decision_path", [])
        if decision_path:
            for step in decision_path:
                if "freshness:" in step:
                    st.markdown(f"⏱️ **Freshness:** {step.split('freshness:')[1].strip()}")
                elif "authority:" in step:
                    st.markdown(f"👑 **Authority:** {step.split('authority:')[1].strip()}")
                elif "corroboration:" in step:
                    st.markdown(f"🤝 **Corroboration:** {step.split('corroboration:')[1].strip()}")
                elif "confidence_floor:" in step:
                    st.markdown(f"📏 **Floor Applied:** {step.split('confidence_floor:')[1].strip()}")
                elif "policy_boost:" in step:
                    st.markdown(f"📈 **Policy Boost:** {step.split('policy_boost:')[1].strip()}")
                elif "raw_text_validation:" in step:
                    st.markdown(f"✅ **Raw Text:** {step.split('raw_text_validation:')[1].strip()}")
                elif "superseded" in step.lower() or "deprecated" in step.lower():
                    st.markdown(f"🚫 {step}")

        # Raw text validation
        st.markdown("#### 📄 Raw Text Validation")
        validation = raw_validations.get(selected_field, {})
        if validation:
            if validation.get("found_in_raw"):
                st.success(f"✓ Found in raw text: `{validation.get('raw_matches', [])}`")
            else:
                note = validation.get("note", "")
                if "Skipped" in note:
                    st.info(note)
                else:
                    st.warning("Not found in raw text")
        else:
            st.caption("No validation data")


# =============================================================================
# PAGE 3: CROSS-PAYER COMPARISON
# =============================================================================
def render_cross_payer_comparison(all_data: dict[str, dict]):
    """Render the cross-payer comparison page."""

    st.markdown("## 📊 Cross-Payer Comparison")

    # Payer selection
    payer_keys = sorted(all_data.keys())
    payer_display = {k: all_data[k].get("payer", k.replace("_", " ").title()) for k in payer_keys}

    selected_payers = st.multiselect(
        "Select Payers to Compare (2-3)",
        payer_keys,
        default=payer_keys[:2] if len(payer_keys) >= 2 else payer_keys,
        format_func=lambda x: payer_display[x],
        max_selections=3
    )

    if len(selected_payers) < 2:
        st.info("Select at least 2 payers to compare")
        return

    # Get all drugs across selected payers
    all_drugs = set()
    for pk in selected_payers:
        drugs = all_data[pk].get("all_drugs", {})
        all_drugs.update(drugs.keys())

    selected_drug = st.selectbox("Select Drug", sorted(all_drugs))

    if not selected_drug:
        return

    st.divider()

    # Comparison table
    st.markdown(f"### {selected_drug} - Payer Comparison")

    # Build comparison data
    cols = st.columns(len(selected_payers))

    for i, payer_key in enumerate(selected_payers):
        with cols[i]:
            payer_name = payer_display[payer_key]
            st.markdown(f"#### {payer_name}")

            drug_data = all_data[payer_key].get("all_drugs", {}).get(selected_drug)

            if not drug_data:
                st.caption("Drug not covered")
                continue

            fields = drug_data.get("fields", drug_data)

            # Auth period
            auth_init = fields.get("auth_period_initial_months") or fields.get("auth_period_months")
            auth_renew = fields.get("auth_period_renewal_months")
            if auth_init:
                st.metric("Auth Period (Initial)", f"{auth_init} mo")
            if auth_renew and auth_renew != auth_init:
                st.metric("Auth Period (Renewal)", f"{auth_renew} mo")

            # Requirements
            st.markdown("**Requirements:**")
            if fields.get("step_therapy_required"):
                st.markdown("- ✅ Step therapy")
            else:
                st.markdown("- ❌ No step therapy")

            if fields.get("prior_treatment_failure_required"):
                st.markdown("- ✅ Prior treatment failure")

            if fields.get("specialist_required"):
                st.markdown("- ✅ Specialist required")

            # Biosimilar
            biosim = fields.get("biosimilar_requirement", "not_stated")
            if biosim == "required":
                st.error("Biosimilar: REQUIRED")
            elif biosim == "preferred":
                st.warning("Biosimilar: Preferred")
            else:
                st.caption("Biosimilar: Not stated")

            # Testing
            testing = fields.get("specific_testing", [])
            if testing:
                st.markdown("**Testing:** " + ", ".join(testing))

    st.divider()

    # General payer comparison
    st.markdown("### General Submission Comparison")

    comparison_data = []
    for payer_key in selected_payers:
        payer = all_data[payer_key]
        best_route = payer.get("best_route", {})
        submission = best_route.get("submission", {})
        turnaround = best_route.get("turnaround", {})

        row = {
            "Payer": payer_display[payer_key],
            "Preferred Method": submission.get("preferred_method", "N/A").upper(),
            "Portal URL": submission.get("preferred_url", "N/A"),
            "Fax": submission.get("fallback_fax", "N/A"),
            "Standard Turnaround": turnaround.get("standard", "N/A"),
            "Urgent Turnaround": turnaround.get("urgent", "N/A"),
        }
        comparison_data.append(row)

    st.dataframe(comparison_data, use_container_width=True, hide_index=True)


# =============================================================================
# PAGE 4: PIPELINE INFO
# =============================================================================
def render_pipeline_info(all_data: dict[str, dict]):
    """Render pipeline architecture info."""

    st.markdown("## 🔧 Pipeline Architecture")

    st.markdown("""
    ### Three-Layer Reconciliation Pipeline

    ```
    Raw Sources → Schema Discovery → Supersession Detection → Confidence Scoring → Output
                        ↓                    ↓                      ↓
                  Field families       Deprecated values       Weighted sum:
                  Qualifier pairs      Version detection       - Freshness (35%)
                  Pass-through         Policy updates          - Authority (35%)
                                                               - Corroboration (20%)
                                                               - Policy boost (10%)
    ```

    ### Source Authority Hierarchy

    | Source Type | Authority Weight | Rationale |
    |-------------|------------------|-----------|
    | Denial Letter | 1.0 | Official policy decision |
    | Phone Transcript | 0.75 | Direct from payer rep |
    | Provider Manual | 0.5 | May be outdated |
    | Web Page | 0.5 | May be outdated |

    ### Confidence Floors

    - **Universal Agreement (all sources match):** ≥ 0.85
    - **Post-Supersession (deprecated values excluded):** ≥ 0.75
    - **Single High-Authority Source:** ≥ 0.70
    """)

    st.divider()

    # Pipeline stats
    st.markdown("### 📈 Pipeline Statistics")

    stats_data = []
    for payer_key, payer in all_data.items():
        summary = payer.get("summary", {})
        stats_data.append({
            "Payer": payer.get("payer", payer_key),
            "Fields Discovered": summary.get("total_fields_discovered", 0),
            "Fields Output": summary.get("total_fields_output", 0),
            "Conflicts": summary.get("conflicts_detected", 0),
            "Raw Text Validated": summary.get("fields_validated_against_raw", 0),
            "Focus Drug": summary.get("focus_drug", "N/A"),
            "Drug Count": len(payer.get("all_drugs", {})),
        })

    st.dataframe(stats_data, use_container_width=True, hide_index=True)


# =============================================================================
# MAIN APP
# =============================================================================
def main():
    st.title("🏥 PA Route Reconciliation")

    payers = get_available_payers()

    if not payers:
        st.error(
            "No reconciliation data found. Run the pipeline first:\n\n"
            "```bash\n"
            "python -m reconciliation_v2.main --all\n"
            "```"
        )
        return

    # Load all data for cross-payer features
    all_data = load_all_payer_data()

    # Sidebar - Payer selector
    st.sidebar.markdown("## Settings")
    selected_payer = st.sidebar.selectbox(
        "Select Payer",
        payers,
        format_func=lambda x: x.replace("_", " ").title()
    )

    # Conflict count badge
    data = all_data.get(selected_payer, {})
    conflicts = data.get("summary", {}).get("conflicts_detected", 0)
    if conflicts > 0:
        st.sidebar.warning(f"⚠️ {conflicts} field conflicts")
    else:
        st.sidebar.success("✓ No conflicts")

    # Navigation tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📋 Payer Route",
        "🔍 Audit Trail",
        "📊 Compare Payers",
        "🔧 Pipeline Info"
    ])

    with tab1:
        render_payer_dashboard(data)

    with tab2:
        render_audit_trail(data)

    with tab3:
        render_cross_payer_comparison(all_data)

    with tab4:
        render_pipeline_info(all_data)


if __name__ == "__main__":
    main()
