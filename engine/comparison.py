"""Vergleich aller Steuerklassen-Kombinationen und Jahresausgleich."""

from typing import Optional
from .parameters import TaxYearParams, get_params
from .models import (
    HouseholdInput, PartnerInput, MonthlyResult, SteuerklasseResult, ComparisonResult,
    ElterngeldResult, IndividualTaxResult, UnmarriedComparisonResult,
)
from .elterngeld import calc_elterngeld
from .tax import (
    calc_est, calc_est_with_progressionsvorbehalt,
    calc_est_splitting, calc_est_splitting_with_progressionsvorbehalt,
    calc_soli, calc_kirchensteuer,
)
from .social import calc_social_contributions
from .payroll import calc_monthly_netto, calc_faktor, calc_vorsorgepauschale


def _compute_annual_declaration(
    household: HouseholdInput,
    params: TaxYearParams,
    elterngeld_total: float = 0.0,
) -> dict:
    """Tatsächliche Jahres-ESt via Einkommensteuererklärung (Splittingtabelle).

    Dies ist UNABHÄNGIG von der Steuerklasse — immer das gleiche Ergebnis.

    Returns:
        Dict mit annual_est, annual_soli, annual_kist, combined_zve,
        kindergeld_annual, kinderfreibetrag_vorteil.
    """
    p1 = household.partner1
    p2 = household.partner2

    # Jahresbrutto
    brutto1 = p1.brutto_annual
    brutto2 = p2.brutto_annual

    # Weitere Einkünfte
    brutto1 += p1.weitere_einkuenfte
    brutto2 += p2.weitere_einkuenfte

    # Werbungskosten
    wk1 = max(params.werbungskosten_pauschale, params.werbungskosten_pauschale + p1.werbungskosten_ueber_pauschale)
    wk2 = max(params.werbungskosten_pauschale, params.werbungskosten_pauschale + p2.werbungskosten_ueber_pauschale)

    # Sonderausgaben (Pauschale für Zusammenveranlagung)
    sa = 2 * params.sonderausgaben_pauschale

    # Vorsorgeaufwendungen (tatsächliche SV-Beiträge * 12)
    # Durchschnittliches Monatsbrutto (brutto_annual / 12) verwenden,
    # damit annual SV korrekt ist (auch bei >12 Gehältern).
    sv1 = calc_social_contributions(
        p1.brutto_monthly_avg, params, kinder=household.kinder,
        is_beamter=p1.is_beamter, is_pkv=p1.is_pkv,
        pkv_monthly=p1.pkv_monthly, kv_zusatzbeitrag=p1.kv_zusatzbeitrag,
    )
    sv2 = calc_social_contributions(
        p2.brutto_monthly_avg, params, kinder=household.kinder,
        is_beamter=p2.is_beamter, is_pkv=p2.is_pkv,
        pkv_monthly=p2.pkv_monthly, kv_zusatzbeitrag=p2.kv_zusatzbeitrag,
    )

    # Bei der Einkommensteuererklärung: RV-Beiträge voll absetzbar (seit 2023)
    # KV-Basisbeitrag (ohne Krankengeld) + PV absetzbar
    # Vereinfacht: alle AN-SV-Beiträge als Vorsorge
    vorsorge1 = sv1.total_an * 12
    vorsorge2 = sv2.total_an * 12

    # Gemeinsames zvE
    combined_income = brutto1 + brutto2
    combined_abzuege = wk1 + wk2 + sa + vorsorge1 + vorsorge2
    combined_zve = max(0, combined_income - combined_abzuege)

    # Elterngeld (Progressionsvorbehalt) — Betrag wird vom Aufrufer übergeben

    # ESt via Splittingtabelle
    if elterngeld_total > 0:
        annual_est = calc_est_splitting_with_progressionsvorbehalt(
            combined_zve, elterngeld_total, params
        )
    else:
        annual_est = calc_est_splitting(combined_zve, params)

    # Günstigerprüfung: Kinderfreibetrag vs. Kindergeld
    kindergeld_annual = household.kinder * params.kindergeld_per_child_monthly * 12
    kinderfreibetrag_total = household.kinder * params.kinderfreibetrag_couple

    # Berechne ESt MIT Kinderfreibetrag
    zve_with_kfb = max(0, combined_zve - kinderfreibetrag_total)
    if elterngeld_total > 0:
        est_with_kfb = calc_est_splitting_with_progressionsvorbehalt(
            zve_with_kfb, elterngeld_total, params
        )
    else:
        est_with_kfb = calc_est_splitting(zve_with_kfb, params)

    # Steuervorteil durch Kinderfreibetrag
    kfb_steuervorteil = annual_est - est_with_kfb

    # Günstigerprüfung: Wenn Kinderfreibetrag mehr Vorteil bringt als Kindergeld
    use_kinderfreibetrag = kfb_steuervorteil > kindergeld_annual and household.kinder > 0

    if use_kinderfreibetrag:
        # Kinderfreibetrag wird angewandt, Kindergeld muss zurückgezahlt werden
        annual_est = est_with_kfb
        # Effektiv: Kindergeld wurde schon ausgezahlt, wird gegen KFB verrechnet
        # In der Steuererklärung: ESt wird um KFB reduziert, aber Kindergeld wird hinzugerechnet
        # Netto-Vorteil: kfb_steuervorteil - kindergeld_annual
        kindergeld_annual_effective = kindergeld_annual  # wird trotzdem ausgezahlt
    else:
        kindergeld_annual_effective = kindergeld_annual

    # Soli auf finale ESt
    annual_soli = calc_soli(annual_est, params, is_couple=True)

    # Kirchensteuer
    annual_kist = 0.0
    if p1.kirchensteuer:
        annual_kist += calc_kirchensteuer(annual_est / 2, household.bundesland, params)
    if p2.kirchensteuer:
        annual_kist += calc_kirchensteuer(annual_est / 2, household.bundesland, params)

    return {
        "annual_est": annual_est,
        "annual_soli": annual_soli,
        "annual_kist": annual_kist,
        "combined_zve": combined_zve,
        "kindergeld_annual": kindergeld_annual_effective,
        "use_kinderfreibetrag": use_kinderfreibetrag,
        "kfb_steuervorteil": kfb_steuervorteil,
    }


def _compute_individual_declaration(
    partner: PartnerInput,
    params: TaxYearParams,
    bundesland: str,
    kinder: int,
    elterngeld_annual: float = 0.0,
) -> IndividualTaxResult:
    """Vereinfachte Einzelveranlagung für einen Partner."""
    income = partner.brutto_annual + partner.weitere_einkuenfte
    wk = max(
        params.werbungskosten_pauschale,
        params.werbungskosten_pauschale + partner.werbungskosten_ueber_pauschale,
    )
    sv = calc_social_contributions(
        partner.brutto_monthly_avg, params, kinder=kinder,
        is_beamter=partner.is_beamter, is_pkv=partner.is_pkv,
        pkv_monthly=partner.pkv_monthly, kv_zusatzbeitrag=partner.kv_zusatzbeitrag,
    )
    vorsorge = sv.total_an * 12
    zve = max(0, income - wk - params.sonderausgaben_pauschale - vorsorge)

    if elterngeld_annual > 0:
        annual_est = calc_est_with_progressionsvorbehalt(zve, elterngeld_annual, params)
    else:
        annual_est = calc_est(zve, params)

    annual_soli = calc_soli(annual_est, params, is_couple=False)
    annual_kist = calc_kirchensteuer(annual_est, bundesland, params) if partner.kirchensteuer else 0.0
    total_tax = round(annual_est + annual_soli + annual_kist, 2)

    return IndividualTaxResult(
        annual_est=annual_est,
        annual_soli=annual_soli,
        annual_kist=annual_kist,
        total_tax=total_tax,
    )


def _compute_unmarried_comparison(
    household: HouseholdInput,
    params: TaxYearParams,
    declaration: dict,
    elterngeld_p1: ElterngeldResult,
    elterngeld_p2: ElterngeldResult,
) -> UnmarriedComparisonResult:
    """Vereinfachter Vergleich: Ehegattensplitting vs. zwei Einzelveranlagungen."""
    p1_tax = _compute_individual_declaration(
        household.partner1, params, household.bundesland, household.kinder,
        elterngeld_annual=elterngeld_p1.elterngeld_annual,
    )
    p2_tax = _compute_individual_declaration(
        household.partner2, params, household.bundesland, household.kinder,
        elterngeld_annual=elterngeld_p2.elterngeld_annual,
    )

    married_total = round(
        declaration["annual_est"] + declaration["annual_soli"] + declaration["annual_kist"],
        2,
    )
    unmarried_total = round(p1_tax.total_tax + p2_tax.total_tax, 2)

    return UnmarriedComparisonResult(
        married_total_tax=married_total,
        unmarried_total_tax=unmarried_total,
        splitting_benefit=round(unmarried_total - married_total, 2),
        partner1=p1_tax,
        partner2=p2_tax,
    )


def _build_steuerklasse_result(
    combo_label: str,
    sk1: int,
    sk2: int,
    household: HouseholdInput,
    params: TaxYearParams,
    declaration: dict,
    elterngeld_p1: ElterngeldResult = None,
    elterngeld_p2: ElterngeldResult = None,
    faktor: Optional[float] = None,
) -> SteuerklasseResult:
    """Ergebnis für eine Steuerklassen-Kombination erstellen."""
    p1 = household.partner1
    p2 = household.partner2

    common = dict(
        bundesland=household.bundesland,
        kinder=household.kinder,
    )

    # Monatliches Netto pro Partner (basierend auf Gehaltsabrechnung)
    # brutto_monthly = brutto_annual / anzahl_gehaelter (Payslip-Betrag)
    # brutto_annual wird separat übergeben für korrekte LSt-Berechnung
    monthly_p1 = calc_monthly_netto(
        p1.brutto_monthly, sk1, params,
        kirchensteuer=p1.kirchensteuer,
        is_beamter=p1.is_beamter, is_pkv=p1.is_pkv,
        pkv_monthly=p1.pkv_monthly, kv_zusatzbeitrag=p1.kv_zusatzbeitrag,
        faktor=faktor if sk1 == 4 and faktor else None,
        brutto_annual=p1.brutto_annual,
        payroll_periods=p1.anzahl_gehaelter,
        **common,
    )
    monthly_p2 = calc_monthly_netto(
        p2.brutto_monthly, sk2, params,
        kirchensteuer=p2.kirchensteuer,
        is_beamter=p2.is_beamter, is_pkv=p2.is_pkv,
        pkv_monthly=p2.pkv_monthly, kv_zusatzbeitrag=p2.kv_zusatzbeitrag,
        faktor=faktor if sk2 == 4 and faktor else None,
        brutto_annual=p2.brutto_annual,
        payroll_periods=p2.anzahl_gehaelter,
        **common,
    )

    hh_monthly = round(monthly_p1.netto + monthly_p2.netto, 2)

    # Jährliches Netto: direkt aus Jahresbrutto berechnen, nicht monthly * 12
    # (bei >12 Gehältern wäre monthly * 12 zu niedrig)
    # Steuern: LSt pro Gehaltsabrechnung * Anzahl Gehälter = Jahres-LSt
    # SV: auf brutto_monthly_avg (= brutto_annual/12) * 12 für korrekte Jahres-SV
    sv_p1_avg = calc_social_contributions(
        p1.brutto_monthly_avg, params, kinder=household.kinder,
        is_beamter=p1.is_beamter, is_pkv=p1.is_pkv,
        pkv_monthly=p1.pkv_monthly, kv_zusatzbeitrag=p1.kv_zusatzbeitrag,
    )
    sv_p2_avg = calc_social_contributions(
        p2.brutto_monthly_avg, params, kinder=household.kinder,
        is_beamter=p2.is_beamter, is_pkv=p2.is_pkv,
        pkv_monthly=p2.pkv_monthly, kv_zusatzbeitrag=p2.kv_zusatzbeitrag,
    )
    annual_taxes_p1 = (monthly_p1.lohnsteuer + monthly_p1.soli + monthly_p1.kirchensteuer) * p1.anzahl_gehaelter
    annual_taxes_p2 = (monthly_p2.lohnsteuer + monthly_p2.soli + monthly_p2.kirchensteuer) * p2.anzahl_gehaelter
    annual_netto_p1 = p1.brutto_annual - annual_taxes_p1 - sv_p1_avg.total_an * 12
    annual_netto_p2 = p2.brutto_annual - annual_taxes_p2 - sv_p2_avg.total_an * 12
    hh_annual = round(annual_netto_p1 + annual_netto_p2, 2)

    # Jährlich einbehalten (LSt + Soli + KiSt)
    withheld_p1 = (monthly_p1.lohnsteuer + monthly_p1.soli + monthly_p1.kirchensteuer) * p1.anzahl_gehaelter
    withheld_p2 = (monthly_p2.lohnsteuer + monthly_p2.soli + monthly_p2.kirchensteuer) * p2.anzahl_gehaelter
    total_withheld = round(withheld_p1 + withheld_p2, 2)

    # Tatsächliche Jahressteuer (gleich für alle Kombis)
    actual_tax = declaration["annual_est"] + declaration["annual_soli"] + declaration["annual_kist"]

    # Differenz: positiv = Erstattung, negativ = Nachzahlung
    difference = round(total_withheld - actual_tax, 2)

    eg_p1 = elterngeld_p1 or ElterngeldResult()
    eg_p2 = elterngeld_p2 or ElterngeldResult()
    kindergeld_monthly = declaration["kindergeld_annual"] / 12

    hh_monthly_verfuegbar = round(
        hh_monthly + eg_p1.elterngeld_monthly + eg_p2.elterngeld_monthly + kindergeld_monthly, 2
    )
    hh_annual_verfuegbar = round(
        hh_annual + eg_p1.elterngeld_annual + eg_p2.elterngeld_annual + declaration["kindergeld_annual"], 2
    )

    return SteuerklasseResult(
        combo_label=combo_label,
        steuerklasse_p1=sk1,
        steuerklasse_p2=sk2,
        partner1_monthly=monthly_p1,
        partner2_monthly=monthly_p2,
        household_monthly_netto=hh_monthly,
        household_annual_netto=hh_annual,
        elterngeld_p1=eg_p1,
        elterngeld_p2=eg_p2,
        household_monthly_verfuegbar=hh_monthly_verfuegbar,
        household_annual_verfuegbar=hh_annual_verfuegbar,
        annual_est_splitting=declaration["annual_est"],
        annual_soli_splitting=declaration["annual_soli"],
        annual_kist_splitting=declaration["annual_kist"],
        total_withheld_annual=total_withheld,
        annual_difference=difference,
        faktor=faktor,
    )


def compare_steuerklassen(household: HouseholdInput) -> ComparisonResult:
    """Alle Steuerklassen-Kombinationen vergleichen.

    Berechnet für 3/5, 5/3, 4/4 und 4+Faktor:
    - Monatliches Netto pro Partner
    - Jährliche Steuererstattung oder Nachzahlung
    - Empfehlung

    Args:
        household: Eingabedaten des Haushalts.

    Returns:
        ComparisonResult mit allen Ergebnissen.
    """
    params = get_params(household.year)
    p1 = household.partner1
    p2 = household.partner2

    # Elterngeld berechnen (aus dem Brutto VOR der Geburt)
    eg_p1 = calc_elterngeld(
        p1.elterngeld_brutto_annual, p1.elterngeld_typ, params,
        kirchensteuer=p1.kirchensteuer, bundesland=household.bundesland,
        is_beamter=p1.is_beamter, is_pkv=p1.is_pkv,
        pkv_monthly=p1.pkv_monthly, kv_zusatzbeitrag=p1.kv_zusatzbeitrag,
        kinder=household.kinder,
    )
    eg_p2 = calc_elterngeld(
        p2.elterngeld_brutto_annual, p2.elterngeld_typ, params,
        kirchensteuer=p2.kirchensteuer, bundesland=household.bundesland,
        is_beamter=p2.is_beamter, is_pkv=p2.is_pkv,
        pkv_monthly=p2.pkv_monthly, kv_zusatzbeitrag=p2.kv_zusatzbeitrag,
        kinder=household.kinder,
    )
    elterngeld_total = eg_p1.elterngeld_annual + eg_p2.elterngeld_annual

    # Tatsächliche Jahressteuer (gleich für alle Kombis)
    declaration = _compute_annual_declaration(household, params, elterngeld_total=elterngeld_total)
    unmarried_comparison = _compute_unmarried_comparison(
        household, params, declaration, eg_p1, eg_p2,
    )

    # Faktor berechnen
    faktor = calc_faktor(
        p1.brutto_annual, p2.brutto_annual, params,
        is_beamter1=p1.is_beamter, is_beamter2=p2.is_beamter,
        is_pkv1=p1.is_pkv, is_pkv2=p2.is_pkv,
        pkv_monthly1=p1.pkv_monthly, pkv_monthly2=p2.pkv_monthly,
        kv_zusatzbeitrag1=p1.kv_zusatzbeitrag, kv_zusatzbeitrag2=p2.kv_zusatzbeitrag,
        kinder=household.kinder,
    )

    # Alle Kombinationen berechnen
    results = []

    eg_args = dict(elterngeld_p1=eg_p1, elterngeld_p2=eg_p2)

    # SK 3/5
    results.append(_build_steuerklasse_result(
        "3 / 5", 3, 5, household, params, declaration, **eg_args,
    ))

    # SK 5/3
    results.append(_build_steuerklasse_result(
        "5 / 3", 5, 3, household, params, declaration, **eg_args,
    ))

    # SK 4/4
    results.append(_build_steuerklasse_result(
        "4 / 4", 4, 4, household, params, declaration, **eg_args,
    ))

    # SK 4+Faktor / 4+Faktor
    results.append(_build_steuerklasse_result(
        f"4+F / 4+F (F={faktor:.3f})", 4, 4, household, params, declaration,
        **eg_args, faktor=faktor,
    ))

    # Empfehlung generieren
    recommendation = _generate_recommendation(results, declaration)

    return ComparisonResult(
        household=household,
        results=results,
        annual_est_actual=declaration["annual_est"],
        annual_soli_actual=declaration["annual_soli"],
        annual_kist_actual=declaration["annual_kist"],
        kindergeld_annual=declaration["kindergeld_annual"],
        elterngeld_p1=eg_p1,
        elterngeld_p2=eg_p2,
        unmarried_comparison=unmarried_comparison,
        recommendation=recommendation,
    )


def _generate_recommendation(results: list, declaration: dict) -> str:
    """Empfehlung basierend auf den Ergebnissen generieren."""
    # Sortiere nach monatlichem Haushaltsnetto (absteigend)
    sorted_by_monthly = sorted(results, key=lambda r: r.household_monthly_netto, reverse=True)
    best_monthly = sorted_by_monthly[0]

    # Finde die Kombination mit der geringsten Nachzahlung / höchsten Erstattung
    sorted_by_diff = sorted(results, key=lambda r: abs(r.annual_difference))
    best_balanced = sorted_by_diff[0]

    lines = []
    lines.append(
        f"Höchstes monatliches Haushaltsnetto: {best_monthly.combo_label} "
        f"mit {best_monthly.household_monthly_netto:,.2f} EUR/Monat"
    )

    if best_monthly.annual_difference < 0:
        lines.append(
            f"  Aber: Nachzahlung von {abs(best_monthly.annual_difference):,.2f} EUR "
            f"bei der Steuererklärung"
        )

    lines.append(
        f"Geringste Abweichung zum Jahresausgleich: {best_balanced.combo_label} "
        f"(Differenz: {best_balanced.annual_difference:+,.2f} EUR)"
    )

    lines.append("")
    lines.append(
        "Wichtig: Die jährliche Steuerlast ist bei allen Steuerklassen-Kombinationen "
        "identisch. Der Unterschied liegt nur im monatlichen Cashflow. "
        "Bei der Steuererklärung wird immer der Splittingtarif angewandt."
    )

    if declaration.get("use_kinderfreibetrag"):
        lines.append(
            f"  Kinderfreibetrag ist günstiger als Kindergeld "
            f"(Vorteil: {declaration['kfb_steuervorteil'] - declaration['kindergeld_annual']:,.2f} EUR)"
        )

    return "\n".join(lines)
