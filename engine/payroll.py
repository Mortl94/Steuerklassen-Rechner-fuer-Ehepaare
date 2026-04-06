"""Monatliche Lohnsteuer-Berechnung pro Steuerklasse.

Berechnet die monatlichen Abzüge (Lohnsteuer, Soli, KiSt) und das Netto
unter Berücksichtigung der Steuerklasse und Sozialversicherung.
"""

from typing import Optional
from .parameters import TaxYearParams
from .tax import calc_est, calc_est_splitting, calc_soli, calc_kirchensteuer
from .social import calc_social_contributions, SocialContributions
from .models import MonthlyResult


def calc_vorsorgepauschale(
    brutto_annual: float,
    params: TaxYearParams,
    steuerklasse: int = 4,
    is_beamter: bool = False,
    is_pkv: bool = False,
    pkv_monthly: float = 0.0,
    kv_zusatzbeitrag: Optional[float] = None,
    kinder: int = 0,
) -> float:
    """Vereinfachte Vorsorgepauschale für den Lohnsteuerabzug.

    Besteht aus:
    - RV-Anteil (AN-Anteil der Rentenversicherung)
    - KV+PV-Anteil (AN-Anteil Kranken- und Pflegeversicherung)

    Args:
        brutto_annual: Jahresbrutto.
        params: Steuerparameter.
        steuerklasse: Steuerklasse (für Mindestvorsorgepauschale).
        is_beamter: Beamter?
        is_pkv: Privat versichert?
        pkv_monthly: PKV-Monatsbeitrag.
        kv_zusatzbeitrag: Individueller Zusatzbeitrag.
        kinder: Anzahl Kinder.

    Returns:
        Jährliche Vorsorgepauschale.
    """
    if is_beamter:
        # Beamte: nur PKV als Vorsorge
        if is_pkv:
            return pkv_monthly * 12
        return 0.0

    zusatzbeitrag = kv_zusatzbeitrag if kv_zusatzbeitrag is not None else params.kv_zusatzbeitrag_avg

    # RV-Anteil: AN-Anteil bis BBG
    rv_brutto = min(brutto_annual, params.rv_bbg_annual)
    rv_an = rv_brutto * params.rv_rate / 2

    # KV-Anteil: AN-Anteil bis BBG
    kv_bbg = params.kv_bbg_annual
    kv_brutto = min(brutto_annual, kv_bbg)

    if is_pkv:
        kv_an = pkv_monthly * 12
    else:
        kv_an_rate = (params.kv_general_rate + zusatzbeitrag) / 2
        kv_an = kv_brutto * kv_an_rate

    # PV-Anteil
    from .social import calc_pv_employee_rate
    pv_an_rate = calc_pv_employee_rate(params, kinder)
    pv_brutto = min(brutto_annual, params.pv_bbg_annual)
    pv_an = pv_brutto * pv_an_rate

    # Mindestvorsorgepauschale (12% des Bruttos, max 1.900/3.000)
    mindest_grenze = 3_000 if steuerklasse == 3 else 1_900
    mindest_kv_pv = min(brutto_annual * 0.12, mindest_grenze)

    kv_pv_total = kv_an + pv_an
    kv_pv_ansatz = max(kv_pv_total, mindest_kv_pv)

    return rv_an + kv_pv_ansatz


def calc_annual_lohnsteuer(
    brutto_annual: float,
    steuerklasse: int,
    params: TaxYearParams,
    is_beamter: bool = False,
    is_pkv: bool = False,
    pkv_monthly: float = 0.0,
    kv_zusatzbeitrag: Optional[float] = None,
    kinder: int = 0,
) -> int:
    """Jährliche Lohnsteuer für eine Steuerklasse berechnen.

    Args:
        brutto_annual: Jahresbrutto.
        steuerklasse: 3, 4 oder 5.
        params: Steuerparameter.

    Returns:
        Jährliche Lohnsteuer in Euro.
    """
    # Werbungskostenpauschale
    wk = params.werbungskosten_pauschale

    # Sonderausgabenpauschale
    sa = params.sonderausgaben_pauschale_sk3 if steuerklasse == 3 else params.sonderausgaben_pauschale

    # Vorsorgepauschale
    vp = calc_vorsorgepauschale(
        brutto_annual, params, steuerklasse,
        is_beamter, is_pkv, pkv_monthly, kv_zusatzbeitrag, kinder,
    )

    # Zu versteuerndes Einkommen
    zve = brutto_annual - wk - sa - vp
    zve = max(0, zve)

    # ESt nach Tarif je Steuerklasse
    if steuerklasse == 3:
        # Splittingtarif: doppelter Grundfreibetrag
        est = calc_est_splitting(zve, params)
    elif steuerklasse == 5:
        # Kein Grundfreibetrag: Berechnung mit Grundfreibetrag = 0
        est = _calc_est_sk5(zve, params)
    else:
        # SK 4 (und SK 1): Grundtabelle
        est = calc_est(zve, params)

    return est


def _calc_est_sk5(zve: float, params: TaxYearParams) -> int:
    """ESt-Berechnung für Steuerklasse 5 (ohne Grundfreibetrag).

    In SK 5 wird der Grundfreibetrag nicht gewährt. Die Berechnung
    erfolgt so, als ob das gesamte zvE ab Euro 0 besteuert wird.
    Vereinfachte Umsetzung: Tarif ab Zone 2 anwenden.
    """
    zve = int(max(0, zve))
    if zve <= 0:
        return 0

    # Berechne die Steuer, die auf den Grundfreibetrag entfallen würde,
    # wenn er besteuert würde, und addiere sie zur normalen Steuer.
    # Alternative Methode: Verwende den Tarif ohne Nullzone.

    # Methode: zvE wird durch den Tarif geschickt, wobei der Grundfreibetrag
    # als bereits verbraucht gilt (durch SK 3 des Partners).
    # Praktisch: Wende den Grenzsteuersatz ab Euro 1 an.

    # Vereinfachter Ansatz: Nutze den normalen Tarif, aber verschiebe das
    # zvE um den Grundfreibetrag nach oben.
    shifted_zve = zve + params.grundfreibetrag
    est_shifted = calc_est(shifted_zve, params)
    est_grundfrei = calc_est(params.grundfreibetrag, params)  # = 0
    return est_shifted - est_grundfrei  # = est_shifted


def calc_faktor(
    brutto1_annual: float,
    brutto2_annual: float,
    params: TaxYearParams,
    is_beamter1: bool = False,
    is_beamter2: bool = False,
    is_pkv1: bool = False,
    is_pkv2: bool = False,
    pkv_monthly1: float = 0.0,
    pkv_monthly2: float = 0.0,
    kv_zusatzbeitrag1: Optional[float] = None,
    kv_zusatzbeitrag2: Optional[float] = None,
    kinder: int = 0,
) -> float:
    """Faktor für das Faktorverfahren (SK 4+Faktor) berechnen.

    Faktor = Splitting-ESt / (SK4-ESt Partner1 + SK4-ESt Partner2)
    Der Faktor ist immer <= 1,0 und wird auf 3 Dezimalstellen abgerundet.
    """
    common_kwargs1 = dict(
        is_beamter=is_beamter1, is_pkv=is_pkv1,
        pkv_monthly=pkv_monthly1, kv_zusatzbeitrag=kv_zusatzbeitrag1,
        kinder=kinder,
    )
    common_kwargs2 = dict(
        is_beamter=is_beamter2, is_pkv=is_pkv2,
        pkv_monthly=pkv_monthly2, kv_zusatzbeitrag=kv_zusatzbeitrag2,
        kinder=kinder,
    )

    # SK 4 Lohnsteuer pro Partner
    lst_sk4_p1 = calc_annual_lohnsteuer(brutto1_annual, 4, params, **common_kwargs1)
    lst_sk4_p2 = calc_annual_lohnsteuer(brutto2_annual, 4, params, **common_kwargs2)
    sum_sk4 = lst_sk4_p1 + lst_sk4_p2

    if sum_sk4 <= 0:
        return 1.0

    # Gemeinsame Vorsorgepauschale für Splitting-Berechnung
    # Vereinfacht: Summe der individuellen Vorsorgepauschalen
    vp1 = calc_vorsorgepauschale(brutto1_annual, params, 4, **common_kwargs1)
    vp2 = calc_vorsorgepauschale(brutto2_annual, params, 4, **common_kwargs2)

    combined_brutto = brutto1_annual + brutto2_annual
    combined_wk = 2 * params.werbungskosten_pauschale
    combined_sa = 2 * params.sonderausgaben_pauschale
    combined_vp = vp1 + vp2

    combined_zve = max(0, combined_brutto - combined_wk - combined_sa - combined_vp)
    est_splitting = calc_est_splitting(combined_zve, params)

    faktor = est_splitting / sum_sk4
    # Auf 3 Dezimalstellen abrunden, max 1.0
    faktor = min(faktor, 1.0)
    faktor = int(faktor * 1000) / 1000

    return faktor


def calc_monthly_netto(
    brutto_monthly: float,
    steuerklasse: int,
    params: TaxYearParams,
    bundesland: str = "Bayern",
    kirchensteuer: bool = False,
    kinder: int = 0,
    is_beamter: bool = False,
    is_pkv: bool = False,
    pkv_monthly: float = 0.0,
    kv_zusatzbeitrag: Optional[float] = None,
    faktor: Optional[float] = None,
) -> MonthlyResult:
    """Monatliches Netto berechnen.

    Args:
        brutto_monthly: Monatliches Brutto.
        steuerklasse: 3, 4 oder 5.
        params: Steuerparameter.
        bundesland: Bundesland (für Kirchensteuer).
        kirchensteuer: Kirchensteuerpflichtig?
        kinder: Anzahl Kinder.
        is_beamter: Beamter?
        is_pkv: Privat versichert?
        pkv_monthly: PKV-Monatsbeitrag.
        kv_zusatzbeitrag: Individueller Zusatzbeitrag.
        faktor: Faktor für SK 4+Faktor.

    Returns:
        MonthlyResult mit allen Abzügen und Netto.
    """
    brutto_annual = brutto_monthly * 12

    # Jährliche Lohnsteuer
    lst_annual = calc_annual_lohnsteuer(
        brutto_annual, steuerklasse, params,
        is_beamter=is_beamter, is_pkv=is_pkv,
        pkv_monthly=pkv_monthly, kv_zusatzbeitrag=kv_zusatzbeitrag,
        kinder=kinder,
    )

    # Faktorverfahren anwenden
    if faktor is not None and steuerklasse == 4:
        lst_annual = int(lst_annual * faktor)

    # Soli auf Lohnsteuer
    soli_annual = calc_soli(lst_annual, params, is_couple=False)

    # Kirchensteuer auf Lohnsteuer
    kist_annual = 0.0
    if kirchensteuer:
        kist_annual = calc_kirchensteuer(lst_annual, bundesland, params)

    # Monatliche Steuerbeträge
    lst_monthly = round(lst_annual / 12, 2)
    soli_monthly = round(soli_annual / 12, 2)
    kist_monthly = round(kist_annual / 12, 2)

    # Sozialversicherung
    sv = calc_social_contributions(
        brutto_monthly, params, kinder=kinder,
        is_beamter=is_beamter, is_pkv=is_pkv,
        pkv_monthly=pkv_monthly, kv_zusatzbeitrag=kv_zusatzbeitrag,
    )

    # Netto
    netto = brutto_monthly - lst_monthly - soli_monthly - kist_monthly - sv.total_an

    return MonthlyResult(
        brutto=brutto_monthly,
        lohnsteuer=lst_monthly,
        soli=soli_monthly,
        kirchensteuer=kist_monthly,
        kv_an=sv.kv_an,
        rv_an=sv.rv_an,
        av_an=sv.av_an,
        pv_an=sv.pv_an,
        netto=round(netto, 2),
    )
