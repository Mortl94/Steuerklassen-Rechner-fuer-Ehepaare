"""Einkommensteuer, Solidaritätszuschlag und Kirchensteuer.

Implementiert die offiziellen Formeln nach §32a EStG.
"""

import math
from .parameters import TaxYearParams


def calc_est(zve: float, params: TaxYearParams) -> int:
    """Einkommensteuer nach §32a EStG berechnen.

    Args:
        zve: Zu versteuerndes Einkommen (auf volle Euro abgerundet).
        params: Steuerparameter des Jahres.

    Returns:
        Einkommensteuer in Euro (abgerundet auf volle Euro).
    """
    zve = int(max(0, zve))

    # Zone 1: Nullzone
    if zve <= params.grundfreibetrag:
        return 0

    # Zone 2: Erste Progressionszone
    if zve <= params.zone2_upper:
        y = (zve - params.zone2_offset) / 10_000
        est = (params.zone2_a * y + params.zone2_b) * y
        return int(est)

    # Zone 3: Zweite Progressionszone
    if zve <= params.zone3_upper:
        z = (zve - params.zone3_offset) / 10_000
        est = (params.zone3_a * z + params.zone3_b) * z + params.zone3_constant
        return int(est)

    # Zone 4: Proportionalzone 42%
    if zve <= params.zone4_upper:
        est = params.zone4_rate * zve - params.zone4_offset
        return int(est)

    # Zone 5: Reichensteuer 45%
    est = params.zone5_rate * zve - params.zone5_offset
    return int(est)


def calc_est_splitting(combined_zve: float, params: TaxYearParams) -> int:
    """Einkommensteuer nach Splittingtarif (Ehegattensplitting).

    Args:
        combined_zve: Gemeinsames zu versteuerndes Einkommen beider Partner.
        params: Steuerparameter des Jahres.

    Returns:
        Einkommensteuer in Euro.
    """
    return 2 * calc_est(combined_zve / 2, params)


def calc_soli(est: float, params: TaxYearParams, is_couple: bool = False) -> float:
    """Solidaritätszuschlag berechnen.

    Seit 2021 mit Freigrenze und Milderungszone.

    Args:
        est: Einkommensteuer-Betrag.
        params: Steuerparameter des Jahres.
        is_couple: True für zusammenveranlagte Ehepaare.

    Returns:
        Solidaritätszuschlag in Euro (auf Cent gerundet).
    """
    if est <= 0:
        return 0.0

    freigrenze = params.soli_freigrenze_couple if is_couple else params.soli_freigrenze_single

    if est <= freigrenze:
        return 0.0

    # Voller Soli
    soli_full = est * params.soli_rate

    # Milderungszone: max. 11,9% des Betrags über der Freigrenze
    soli_milderung = (est - freigrenze) * params.soli_milderung_rate

    soli = min(soli_full, soli_milderung)

    # Abrunden auf Cent
    return math.floor(soli * 100) / 100


def calc_kirchensteuer(
    est: float,
    bundesland: str,
    params: TaxYearParams,
) -> float:
    """Kirchensteuer berechnen.

    Args:
        est: Einkommensteuer-Betrag (Bemessungsgrundlage).
        bundesland: Bundesland für den Kirchensteuersatz.
        params: Steuerparameter des Jahres.

    Returns:
        Kirchensteuer in Euro.
    """
    if est <= 0:
        return 0.0

    rate = (
        params.kirchensteuer_rate_bayern_bw
        if bundesland in params.laender_8_prozent
        else params.kirchensteuer_rate_other
    )
    return round(est * rate, 2)


def calc_est_with_progressionsvorbehalt(
    regular_zve: float,
    steuerfreie_einkuenfte: float,
    params: TaxYearParams,
) -> int:
    """ESt unter Berücksichtigung des Progressionsvorbehalts.

    Steuerfreie Einkünfte (z.B. Elterngeld) erhöhen den Steuersatz
    auf das reguläre Einkommen.

    Args:
        regular_zve: Zu versteuerndes Einkommen (ohne steuerfreie Einkünfte).
        steuerfreie_einkuenfte: Steuerfreie Einkünfte (z.B. Elterngeld).
        params: Steuerparameter des Jahres.

    Returns:
        ESt unter Berücksichtigung des Progressionsvorbehalts.
    """
    if steuerfreie_einkuenfte <= 0 or regular_zve <= 0:
        return calc_est(regular_zve, params)

    # Fiktives Gesamteinkommen
    total = regular_zve + steuerfreie_einkuenfte

    # Steuersatz auf fiktives Gesamteinkommen
    est_total = calc_est(total, params)
    if total <= 0:
        return 0

    rate = est_total / total

    # Diesen erhöhten Satz auf reguläres Einkommen anwenden
    est = regular_zve * rate
    return int(est)


def calc_est_splitting_with_progressionsvorbehalt(
    combined_regular_zve: float,
    combined_steuerfreie_einkuenfte: float,
    params: TaxYearParams,
) -> int:
    """Splittingtarif mit Progressionsvorbehalt.

    Args:
        combined_regular_zve: Gemeinsames zvE (ohne steuerfreie Einkünfte).
        combined_steuerfreie_einkuenfte: Gemeinsame steuerfreie Einkünfte.
        params: Steuerparameter.

    Returns:
        ESt nach Splitting mit Progressionsvorbehalt.
    """
    half_regular = combined_regular_zve / 2
    half_steuerfrei = combined_steuerfreie_einkuenfte / 2
    return 2 * calc_est_with_progressionsvorbehalt(half_regular, half_steuerfrei, params)
