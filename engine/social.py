"""Sozialversicherungsbeiträge: KV, RV, AV, PV."""

from dataclasses import dataclass
from typing import Optional
from .parameters import TaxYearParams


@dataclass
class SocialContributions:
    """Sozialversicherungsbeiträge (Arbeitnehmer-Anteil)."""
    kv_an: float = 0.0
    rv_an: float = 0.0
    av_an: float = 0.0
    pv_an: float = 0.0

    @property
    def total_an(self) -> float:
        return self.kv_an + self.rv_an + self.av_an + self.pv_an


def calc_pv_employee_rate(
    params: TaxYearParams,
    kinder: int,
) -> float:
    """Pflegeversicherung: AN-Beitragssatz berechnen.

    - Basis: pv_rate_base / 2
    - Kinderlos (0 Kinder): +0,6% Zuschlag (voll AN)
    - 1 Kind: keine Änderung
    - 2-5 Kinder unter 25: -0,25% pro Kind (ab dem 2.)
    - Max. Abschlag: 1,0% (bei 5+ Kindern)

    Returns:
        AN-Beitragssatz als Dezimalzahl (z.B. 0.018 für 1,8%).
    """
    base_an = params.pv_rate_base / 2  # z.B. 0.018

    if kinder == 0:
        # Kinderlosenzuschlag voll auf AN-Seite
        return base_an + params.pv_kinderlos_zuschlag

    if kinder == 1:
        return base_an

    # 2+ Kinder: Abschlag pro Kind (2.-5.)
    eligible_children = min(kinder, 5) - 1  # max 4 Kinder mit Abschlag
    abschlag = eligible_children * params.pv_kind_abschlag
    return max(base_an - abschlag, 0.0)


def calc_social_contributions(
    brutto_monthly: float,
    params: TaxYearParams,
    kinder: int = 0,
    is_beamter: bool = False,
    is_pkv: bool = False,
    pkv_monthly: float = 0.0,
    kv_zusatzbeitrag: Optional[float] = None,
) -> SocialContributions:
    """Sozialversicherungsbeiträge (AN-Anteil) berechnen.

    Args:
        brutto_monthly: Monatliches Bruttogehalt.
        params: Steuerparameter des Jahres.
        kinder: Anzahl Kinder.
        is_beamter: True für Beamte (keine SV-Beiträge außer ggf. PKV).
        is_pkv: True für privat Krankenversicherte.
        pkv_monthly: Monatlicher PKV-Beitrag (AN-Anteil).
        kv_zusatzbeitrag: Individueller Zusatzbeitrag. None = Durchschnitt.

    Returns:
        SocialContributions mit allen AN-Anteilen.
    """
    result = SocialContributions()

    # Beamte: keine gesetzlichen Sozialversicherungsbeiträge
    if is_beamter:
        # Nur PKV-Beitrag (wird direkt als AN-Anteil angegeben)
        if is_pkv:
            result.kv_an = pkv_monthly
        return result

    zusatzbeitrag = kv_zusatzbeitrag if kv_zusatzbeitrag is not None else params.kv_zusatzbeitrag_avg

    # --- Krankenversicherung ---
    kv_bbg_monthly = params.kv_bbg_annual / 12
    kv_brutto = min(brutto_monthly, kv_bbg_monthly)

    if is_pkv:
        # PKV: AN zahlt eigenen Beitrag, kein BBG-bezogener Beitrag
        result.kv_an = pkv_monthly
    else:
        # GKV: Allgemeiner Beitrag + Zusatzbeitrag, jeweils 50/50
        kv_an_rate = (params.kv_general_rate + zusatzbeitrag) / 2
        result.kv_an = round(kv_brutto * kv_an_rate, 2)

    # --- Rentenversicherung ---
    rv_bbg_monthly = params.rv_bbg_annual / 12
    rv_brutto = min(brutto_monthly, rv_bbg_monthly)
    result.rv_an = round(rv_brutto * params.rv_rate / 2, 2)

    # --- Arbeitslosenversicherung ---
    av_bbg_monthly = params.av_bbg_annual / 12
    av_brutto = min(brutto_monthly, av_bbg_monthly)
    result.av_an = round(av_brutto * params.av_rate / 2, 2)

    # --- Pflegeversicherung ---
    pv_bbg_monthly = params.pv_bbg_annual / 12
    pv_brutto = min(brutto_monthly, pv_bbg_monthly)

    if is_pkv:
        # PKV-Versicherte zahlen PV selbst (voller Beitrag)
        # Aber nur bis BBG und der AG-Zuschuss wird separat berechnet
        # Vereinfacht: AN-Anteil wie bei GKV
        pv_an_rate = calc_pv_employee_rate(params, kinder)
        result.pv_an = round(pv_brutto * pv_an_rate, 2)
    else:
        pv_an_rate = calc_pv_employee_rate(params, kinder)
        result.pv_an = round(pv_brutto * pv_an_rate, 2)

    return result
