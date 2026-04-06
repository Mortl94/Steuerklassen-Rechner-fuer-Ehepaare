"""Steuerklassen-Rechner für Ehepaare — Streamlit UI."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from engine.parameters import TAX_YEARS, BUNDESLAENDER
from engine.models import PartnerInput, HouseholdInput, ComparisonResult
from engine.comparison import compare_steuerklassen


def main():
    st.set_page_config(
        page_title="Steuerklassen-Rechner",
        page_icon="💰",
        layout="wide",
    )

    st.title("Steuerklassen-Rechner für Ehepaare")
    st.caption("Vergleich der Steuerklassen 3/5, 5/3, 4/4 und 4+Faktor — keine Steuerberatung")

    # --- Sidebar: Eingaben ---
    household = _render_sidebar()

    if household is None:
        st.info(
            "Bitte geben Sie mindestens für einen Partner ein Bruttogehalt oder "
            "Elterngeld in der Sidebar ein."
        )
        return

    # --- Berechnung ---
    result = compare_steuerklassen(household)

    # --- Tabs ---
    tab1, tab2, tab3, tab4 = st.tabs([
        "Übersicht",
        "Monatsdetails",
        "Jahresausgleich",
        "Visualisierungen",
    ])

    with tab1:
        _render_overview(result)

    with tab2:
        _render_monthly_details(result)

    with tab3:
        _render_annual_settlement(result)

    with tab4:
        _render_charts(result)

    # --- Disclaimer ---
    st.divider()
    st.caption(
        "⚠️ Alle Berechnungen ohne Gewähr. Dies ist keine Steuerberatung. "
        "Die Ergebnisse dienen nur zur Orientierung. Für verbindliche Auskünfte "
        "wenden Sie sich an einen Steuerberater oder das zuständige Finanzamt. "
        "Abweichungen zum tatsächlichen Lohnsteuerabzug sind möglich."
    )


def _render_sidebar() -> HouseholdInput | None:
    """Sidebar mit allen Eingabefeldern rendern."""
    with st.sidebar:
        st.header("Einstellungen")

        year = st.selectbox(
            "Steuerjahr",
            options=sorted(TAX_YEARS.keys(), reverse=True),
            index=0,
        )

        bundesland = st.selectbox("Bundesland", options=BUNDESLAENDER, index=1)  # Bayern

        kinder = st.number_input("Anzahl Kinder", min_value=0, max_value=10, value=0)

        st.divider()

        # --- Partner 1 ---
        st.subheader("Partner 1")
        p1 = _render_partner_input("p1")

        st.divider()

        # --- Partner 2 ---
        st.subheader("Partner 2")
        p2 = _render_partner_input("p2")

    # Mindestens ein Partner braucht Einkommen oder Elterngeld
    has_income = (
        p1.brutto_annual > 0 or p1.elterngeld_monthly > 0
        or p2.brutto_annual > 0 or p2.elterngeld_monthly > 0
    )
    if not has_income:
        return None

    return HouseholdInput(
        partner1=p1,
        partner2=p2,
        year=year,
        bundesland=bundesland,
        kinder=kinder,
    )


def _render_partner_input(key_prefix: str) -> PartnerInput:
    """Eingabefelder für einen Partner rendern."""
    brutto_annual = st.number_input(
        "Jahresbrutto (EUR)",
        min_value=0.0,
        max_value=500_000.0,
        value=0.0,
        step=1_000.0,
        key=f"{key_prefix}_brutto",
        help="Gesamtes Jahresbrutto inkl. 13./14. Gehalt, Weihnachtsgeld, Boni. 0 wenn nur Elterngeld.",
    )

    anzahl_gehaelter = st.number_input(
        "Anzahl Gehälter / Jahr",
        min_value=1, max_value=15, value=12,
        key=f"{key_prefix}_gehaelter",
        help="Wie viele Monatsgehälter pro Jahr? (12 = Standard, 13 = mit Weihnachtsgeld, etc.)",
    )

    if brutto_annual > 0:
        st.caption(f"= {brutto_annual / anzahl_gehaelter:,.2f} EUR pro Gehaltsabrechnung, "
                   f"{brutto_annual / 12:,.2f} EUR durchschnittlich/Monat")

    kirchensteuer = st.checkbox("Kirchensteuer", key=f"{key_prefix}_kist")
    is_beamter = st.checkbox("Beamter/Beamtin", key=f"{key_prefix}_beamter")

    is_pkv = st.checkbox("Privat krankenversichert (PKV)", key=f"{key_prefix}_pkv")
    pkv_monthly = 0.0
    if is_pkv:
        pkv_monthly = st.number_input(
            "PKV-Beitrag / Monat (AN-Anteil, EUR)",
            min_value=0.0, max_value=2_000.0, value=300.0, step=10.0,
            key=f"{key_prefix}_pkv_betrag",
        )

    # Elterngeld (prominent, nicht versteckt)
    elterngeld = st.number_input(
        "Elterngeld / Monat (EUR)",
        min_value=0.0, max_value=2_000.0, value=0.0, step=100.0,
        key=f"{key_prefix}_eg",
        help="Steuerfrei, erhöht aber den Steuersatz auf andere Einkünfte (Progressionsvorbehalt)",
    )

    elterngeld_months = 0
    if elterngeld > 0:
        elterngeld_months = st.number_input(
            "Elterngeld-Monate",
            min_value=1, max_value=24, value=12,
            key=f"{key_prefix}_eg_monate",
        )

    # Erweiterte Optionen
    with st.expander("Erweiterte Optionen"):
        kv_zusatzbeitrag_pct = st.number_input(
            "KV-Zusatzbeitrag (%)",
            min_value=0.0, max_value=10.0, value=0.0, step=0.1,
            help="0 = Durchschnittswert des Jahres verwenden",
            key=f"{key_prefix}_zusatz",
        )
        kv_zusatzbeitrag = kv_zusatzbeitrag_pct / 100 if kv_zusatzbeitrag_pct > 0 else None

        weitere_einkuenfte = st.number_input(
            "Weitere Einkünfte / Jahr (EUR)",
            min_value=0.0, max_value=500_000.0, value=0.0, step=1_000.0,
            key=f"{key_prefix}_weitere",
        )

        werbungskosten = st.number_input(
            "Werbungskosten über Pauschale (EUR)",
            min_value=0.0, max_value=100_000.0, value=0.0, step=100.0,
            help="Nur den Betrag ÜBER der Pauschale von 1.230 EUR angeben",
            key=f"{key_prefix}_wk",
        )

    return PartnerInput(
        brutto_annual=brutto_annual,
        anzahl_gehaelter=anzahl_gehaelter,
        kirchensteuer=kirchensteuer,
        is_beamter=is_beamter,
        is_pkv=is_pkv,
        pkv_monthly=pkv_monthly,
        kv_zusatzbeitrag=kv_zusatzbeitrag,
        weitere_einkuenfte=weitere_einkuenfte,
        werbungskosten_ueber_pauschale=werbungskosten,
        elterngeld_monthly=elterngeld,
        elterngeld_months=elterngeld_months,
    )


# ============================================================
# Tab 1: Übersicht
# ============================================================

def _render_overview(result: ComparisonResult):
    """Tab 1: Übersicht mit Vergleichstabelle und Kernaussage."""
    st.info(
        "**Wichtig:** Die jährliche Steuerlast ist bei **allen** Steuerklassen-Kombinationen "
        "identisch (Splittingtarif). Der Unterschied liegt **nur** im monatlichen Cashflow. "
        "Bei der Steuererklärung wird immer nach Splittingtabelle abgerechnet."
    )

    # Vergleichstabelle
    rows = []
    for r in result.results:
        rows.append({
            "Steuerklasse": r.combo_label,
            "P1 Netto/Mo": f"{r.partner1_monthly.netto:,.2f} €",
            "P2 Netto/Mo": f"{r.partner2_monthly.netto:,.2f} €",
            "Haushalt/Mo": f"{r.household_monthly_netto:,.2f} €",
            "Haushalt/Jahr": f"{r.household_annual_netto:,.2f} €",
            "Erstattung (+) / Nachzahlung (-)": f"{r.annual_difference:+,.2f} €",
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Kindergeld-Info
    if result.kindergeld_annual > 0:
        st.success(f"Kindergeld: {result.kindergeld_annual:,.2f} EUR / Jahr "
                   f"({result.kindergeld_annual / 12:,.2f} EUR / Monat)")

    # Delta-Metriken
    st.subheader("Vergleich: Monatlicher Cashflow")
    cols = st.columns(len(result.results))
    ref_netto = result.results[2].household_monthly_netto  # 4/4 als Referenz

    for i, r in enumerate(result.results):
        delta = r.household_monthly_netto - ref_netto
        cols[i].metric(
            label=f"SK {r.combo_label}",
            value=f"{r.household_monthly_netto:,.0f} €/Mo",
            delta=f"{delta:+,.0f} € vs. 4/4" if abs(delta) > 0.01 else "Referenz",
        )

    # Empfehlung
    st.subheader("Empfehlung")
    st.markdown(result.recommendation.replace("\n", "  \n"))


# ============================================================
# Tab 2: Monatsdetails
# ============================================================

def _render_monthly_details(result: ComparisonResult):
    """Tab 2: Detaillierte Aufschlüsselung Brutto -> Netto."""
    for r in result.results:
        st.subheader(f"Steuerklasse {r.combo_label}")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Partner 1**")
            _render_breakdown_table(r.partner1_monthly)

        with col2:
            st.markdown("**Partner 2**")
            _render_breakdown_table(r.partner2_monthly)

        st.divider()


def _render_breakdown_table(m):
    """Aufschlüsselung eines MonthlyResult als Tabelle."""
    data = {
        "Position": [
            "Bruttogehalt",
            "- Lohnsteuer",
            "- Solidaritätszuschlag",
            "- Kirchensteuer",
            "- Krankenversicherung",
            "- Rentenversicherung",
            "- Arbeitslosenversicherung",
            "- Pflegeversicherung",
            "**= Nettoeinkommen**",
        ],
        "Betrag": [
            f"{m.brutto:,.2f} €",
            f"-{m.lohnsteuer:,.2f} €",
            f"-{m.soli:,.2f} €",
            f"-{m.kirchensteuer:,.2f} €",
            f"-{m.kv_an:,.2f} €",
            f"-{m.rv_an:,.2f} €",
            f"-{m.av_an:,.2f} €",
            f"-{m.pv_an:,.2f} €",
            f"**{m.netto:,.2f} €**",
        ],
    }
    st.dataframe(
        pd.DataFrame(data),
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# Tab 3: Jahresausgleich
# ============================================================

def _render_annual_settlement(result: ComparisonResult):
    """Tab 3: Simulation der Einkommensteuererklärung."""
    st.subheader("Tatsächliche Jahressteuer (Splittingtarif)")

    actual_total = result.annual_est_actual + result.annual_soli_actual + result.annual_kist_actual

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Einkommensteuer", f"{result.annual_est_actual:,.2f} €")
    col2.metric("Solidaritätszuschlag", f"{result.annual_soli_actual:,.2f} €")
    col3.metric("Kirchensteuer", f"{result.annual_kist_actual:,.2f} €")
    col4.metric("Gesamt", f"{actual_total:,.2f} €")

    st.divider()
    st.subheader("Vergleich: Einbehalten vs. Tatsächlich")

    rows = []
    for r in result.results:
        actual = r.annual_est_splitting + r.annual_soli_splitting + r.annual_kist_splitting
        rows.append({
            "Steuerklasse": r.combo_label,
            "Einbehalten (LSt+Soli+KiSt)": f"{r.total_withheld_annual:,.2f} €",
            "Tatsächliche Jahressteuer": f"{actual:,.2f} €",
            "Differenz": f"{r.annual_difference:+,.2f} €",
            "Ergebnis": "Erstattung" if r.annual_difference > 0 else ("Nachzahlung" if r.annual_difference < 0 else "Ausgeglichen"),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.info(
        "**Positiv** = Sie bekommen Geld vom Finanzamt zurück.  \n"
        "**Negativ** = Sie müssen nachzahlen.  \n"
        "Das **4+Faktor-Verfahren** ist darauf ausgelegt, die Differenz zu minimieren."
    )

    # Effektives Jahresergebnis
    st.subheader("Effektives Jahresergebnis (Netto + Erstattung/Nachzahlung)")
    rows_eff = []
    for r in result.results:
        effective = r.household_annual_netto + r.annual_difference
        rows_eff.append({
            "Steuerklasse": r.combo_label,
            "Jahres-Netto (monatl. x 12)": f"{r.household_annual_netto:,.2f} €",
            "Erstattung/Nachzahlung": f"{r.annual_difference:+,.2f} €",
            "Kindergeld": f"+{result.kindergeld_annual:,.2f} €",
            "Effektiv verfügbar": f"{effective + result.kindergeld_annual:,.2f} €",
        })

    st.dataframe(pd.DataFrame(rows_eff), use_container_width=True, hide_index=True)


# ============================================================
# Tab 4: Visualisierungen
# ============================================================

def _render_charts(result: ComparisonResult):
    """Tab 4: Plotly-Charts."""

    # Chart 1: Monatliches Haushaltsnetto
    st.subheader("Monatliches Haushaltsnetto nach Steuerklasse")
    labels = [r.combo_label for r in result.results]
    p1_values = [r.partner1_monthly.netto for r in result.results]
    p2_values = [r.partner2_monthly.netto for r in result.results]

    fig1 = go.Figure(data=[
        go.Bar(name="Partner 1", x=labels, y=p1_values, marker_color="#1f77b4"),
        go.Bar(name="Partner 2", x=labels, y=p2_values, marker_color="#ff7f0e"),
    ])
    fig1.update_layout(
        barmode="stack",
        yaxis_title="Netto / Monat (EUR)",
        xaxis_title="Steuerklasse",
        height=400,
    )
    st.plotly_chart(fig1, use_container_width=True)

    # Chart 2: Jahresausgleich (Erstattung / Nachzahlung)
    st.subheader("Erstattung / Nachzahlung bei Steuererklärung")
    differences = [r.annual_difference for r in result.results]
    colors = ["#2ca02c" if d >= 0 else "#d62728" for d in differences]

    fig2 = go.Figure(data=[
        go.Bar(
            x=labels,
            y=differences,
            marker_color=colors,
            text=[f"{d:+,.0f} €" for d in differences],
            textposition="outside",
        ),
    ])
    fig2.update_layout(
        yaxis_title="Erstattung (+) / Nachzahlung (-) in EUR",
        xaxis_title="Steuerklasse",
        height=400,
    )
    fig2.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig2, use_container_width=True)

    # Chart 3: Aufschlüsselung der monatlichen Abzüge (SK 4/4 als Beispiel)
    st.subheader("Aufschlüsselung monatliche Abzüge")
    selected_sk = st.selectbox(
        "Steuerklasse wählen",
        options=range(len(result.results)),
        format_func=lambda i: result.results[i].combo_label,
        index=2,  # Default: 4/4
    )
    r = result.results[selected_sk]

    for partner_label, m in [("Partner 1", r.partner1_monthly), ("Partner 2", r.partner2_monthly)]:
        fig3 = go.Figure(go.Waterfall(
            name=partner_label,
            orientation="v",
            x=["Brutto", "LSt", "Soli", "KiSt", "KV", "RV", "AV", "PV", "Netto"],
            y=[
                m.brutto,
                -m.lohnsteuer,
                -m.soli,
                -m.kirchensteuer,
                -m.kv_an,
                -m.rv_an,
                -m.av_an,
                -m.pv_an,
                0,
            ],
            measure=["absolute", "relative", "relative", "relative",
                      "relative", "relative", "relative", "relative", "total"],
            text=[
                f"{m.brutto:,.0f}",
                f"-{m.lohnsteuer:,.0f}",
                f"-{m.soli:,.0f}",
                f"-{m.kirchensteuer:,.0f}",
                f"-{m.kv_an:,.0f}",
                f"-{m.rv_an:,.0f}",
                f"-{m.av_an:,.0f}",
                f"-{m.pv_an:,.0f}",
                f"{m.netto:,.0f}",
            ],
            textposition="outside",
            connector={"line": {"color": "rgb(63, 63, 63)"}},
        ))
        fig3.update_layout(
            title=f"{partner_label} — SK {r.combo_label}",
            yaxis_title="EUR / Monat",
            height=400,
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)


if __name__ == "__main__":
    main()
