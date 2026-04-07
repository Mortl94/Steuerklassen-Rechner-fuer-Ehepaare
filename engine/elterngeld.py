"""Elterngeld-Berechnung aus dem Bruttoeinkommen.

Berechnet Elterngeld Basis und Elterngeld Plus automatisch anhand
des Bruttoeinkommens vor der Geburt.

Berechnungsgrundlage:
- Elterngeld-Netto = Brutto - Steuern (SK 4) - Sozialversicherung
  - Werbungskostenpauschale (1/12 von 1.230 EUR)
- Ersatzrate:
  - Netto < 1.000 EUR: 67% (steigt um 0,1% pro 2 EUR unter 1.000)
  - Netto 1.000-1.200 EUR: 67%
  - Netto > 1.200 EUR: 65%
- Elterngeld Basis: Ersatzrate * Netto, min 300 EUR, max 1.800 EUR, 12 Monate
- Elterngeld Plus: Ersatzrate * Netto / 2, min 150 EUR, max 900 EUR, 24 Monate
"""

from .parameters import TaxYearParams
from .models import ElterngeldTyp, ElterngeldResult
from .payroll import calc_annual_lohnsteuer
from .social import calc_social_contributions


def calc_elterngeld_netto(
    brutto_annual: float,
    params: TaxYearParams,
    kirchensteuer: bool = False,
    bundesland: str = "Bayern",
    is_beamter: bool = False,
    is_pkv: bool = False,
    pkv_monthly: float = 0.0,
    kv_zusatzbeitrag: float | None = None,
    kinder: int = 0,
) -> float:
    """Elterngeld-Netto berechnen (Berechnungsgrundlage).

    Das Elterngeld-Netto wird aus dem Brutto vor der Geburt berechnet
    und dient als Basis für die Elterngeld-Höhe.

    Returns:
        Monatliches Elterngeld-Netto.
    """
    if brutto_annual <= 0:
        return 0.0

    brutto_monthly = brutto_annual / 12

    # Werbungskostenpauschale (1/12 von 1.230 EUR) abziehen
    wk_monthly = params.werbungskosten_pauschale / 12
    bemessungs_brutto_monthly = max(0, brutto_monthly - wk_monthly)
    bemessungs_brutto_annual = bemessungs_brutto_monthly * 12

    # Lohnsteuer (SK 4 = Standard für Elterngeld-Berechnung)
    lst_annual = calc_annual_lohnsteuer(
        bemessungs_brutto_annual, 4, params,
        is_beamter=is_beamter, is_pkv=is_pkv,
        pkv_monthly=pkv_monthly, kv_zusatzbeitrag=kv_zusatzbeitrag,
        kinder=kinder,
    )
    lst_monthly = lst_annual / 12

    # Sozialversicherung auf das volle Brutto
    sv = calc_social_contributions(
        brutto_monthly, params, kinder=kinder,
        is_beamter=is_beamter, is_pkv=is_pkv,
        pkv_monthly=pkv_monthly, kv_zusatzbeitrag=kv_zusatzbeitrag,
    )

    netto = brutto_monthly - lst_monthly - sv.total_an
    return max(0, netto)


def calc_ersatzrate(netto_monthly: float) -> float:
    """Ersatzrate für Elterngeld berechnen.

    - Netto < 1.000 EUR: Erhöhung um 0,1% pro 2 EUR unter 1.000, max 100%
    - Netto 1.000 - 1.200 EUR: 67%
    - Netto > 1.200 EUR: 65%

    Returns:
        Ersatzrate als Dezimalzahl (z.B. 0.67).
    """
    if netto_monthly <= 0:
        return 0.67

    if netto_monthly < 1_000:
        # Pro 2 EUR unter 1.000: +0,1% (= +0.001)
        diff = 1_000 - netto_monthly
        zusatz = (diff / 2) * 0.001
        return min(0.67 + zusatz, 1.0)

    if netto_monthly <= 1_200:
        return 0.67

    return 0.65


def calc_elterngeld(
    brutto_annual: float,
    elterngeld_typ: ElterngeldTyp,
    params: TaxYearParams,
    kirchensteuer: bool = False,
    bundesland: str = "Bayern",
    is_beamter: bool = False,
    is_pkv: bool = False,
    pkv_monthly: float = 0.0,
    kv_zusatzbeitrag: float | None = None,
    kinder: int = 0,
) -> ElterngeldResult:
    """Elterngeld berechnen.

    Args:
        brutto_annual: Jahresbrutto VOR der Geburt.
        elterngeld_typ: Basis oder Plus.
        params: Steuerparameter.

    Returns:
        ElterngeldResult mit monatlichem Betrag und Details.
    """
    if elterngeld_typ == ElterngeldTyp.KEIN:
        return ElterngeldResult()

    # Elterngeld-Netto berechnen
    netto = calc_elterngeld_netto(
        brutto_annual, params,
        kirchensteuer=kirchensteuer, bundesland=bundesland,
        is_beamter=is_beamter, is_pkv=is_pkv,
        pkv_monthly=pkv_monthly, kv_zusatzbeitrag=kv_zusatzbeitrag,
        kinder=kinder,
    )

    # Ersatzrate
    rate = calc_ersatzrate(netto)

    # Elterngeld berechnen
    elterngeld_basis = netto * rate

    if elterngeld_typ == ElterngeldTyp.BASIS:
        # Min 300, Max 1.800, 12 Monate
        eg_monthly = max(300, min(elterngeld_basis, 1_800))
        eg_months = 12
    else:
        # Plus: Hälfte des Basis-Betrags, Min 150, Max 900, 24 Monate
        eg_monthly = max(150, min(elterngeld_basis / 2, 900))
        eg_months = 24

    # Mindestbetrag auch bei Brutto = 0
    if brutto_annual <= 0:
        if elterngeld_typ == ElterngeldTyp.BASIS:
            eg_monthly = 300
        else:
            eg_monthly = 150

    return ElterngeldResult(
        elterngeld_monthly=round(eg_monthly, 2),
        elterngeld_months=eg_months,
        elterngeld_typ=elterngeld_typ,
        netto_vor_geburt=round(netto, 2),
        ersatzrate=round(rate, 4),
    )
