"""Jahresabhängige Steuerparameter für 2025 und 2026."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EStZone:
    """Eine Zone des Einkommensteuertarifs nach §32a EStG."""
    lower: int
    upper: int  # use float('inf') for last zone
    # Quadratic zones: (coeff_a * var + coeff_b) * var + constant
    # Linear zones: linear_rate * zve - linear_offset
    base_offset: int = 0       # subtracted from zvE, then / 10_000
    coeff_a: float = 0.0
    coeff_b: float = 0.0
    constant: float = 0.0
    linear_rate: float = 0.0
    linear_offset: float = 0.0


@dataclass(frozen=True)
class TaxYearParams:
    """Alle steuerrelevanten Parameter für ein Steuerjahr."""
    year: int

    # --- Einkommensteuer-Tarif (§32a EStG) ---
    grundfreibetrag: int
    zone2_upper: int
    zone2_offset: int
    zone2_a: float
    zone2_b: float
    zone3_upper: int
    zone3_offset: int
    zone3_a: float
    zone3_b: float
    zone3_constant: float
    zone4_upper: int
    zone4_rate: float
    zone4_offset: float
    zone5_rate: float
    zone5_offset: float

    # --- Solidaritätszuschlag ---
    soli_rate: float = 0.055
    soli_freigrenze_single: int = 0
    soli_freigrenze_couple: int = 0
    soli_milderung_rate: float = 0.119

    # --- Kirchensteuer ---
    kirchensteuer_rate_bayern_bw: float = 0.08
    kirchensteuer_rate_other: float = 0.09

    # --- Krankenversicherung (GKV) ---
    kv_general_rate: float = 0.146
    kv_zusatzbeitrag_avg: float = 0.0
    kv_bbg_annual: int = 0

    # --- Rentenversicherung ---
    rv_rate: float = 0.186
    rv_bbg_annual: int = 0

    # --- Arbeitslosenversicherung ---
    av_rate: float = 0.026
    av_bbg_annual: int = 0  # same as rv_bbg_annual

    # --- Pflegeversicherung ---
    pv_rate_base: float = 0.0
    pv_kinderlos_zuschlag: float = 0.006
    pv_kind_abschlag: float = 0.0025  # pro Kind (2.-5. unter 25)
    pv_bbg_annual: int = 0  # same as kv_bbg_annual

    # --- Versicherungspflichtgrenze ---
    versicherungspflichtgrenze_annual: int = 0

    # --- Pauschalen ---
    werbungskosten_pauschale: int = 1230
    sonderausgaben_pauschale: int = 36
    sonderausgaben_pauschale_sk3: int = 72

    # --- Kindergeld & Kinderfreibetrag ---
    kindergeld_per_child_monthly: float = 0.0
    kinderfreibetrag_couple: float = 0.0

    # --- Bundesländer mit 8% Kirchensteuer ---
    laender_8_prozent: tuple = ("Bayern", "Baden-Württemberg")


# ============================================================
# 2025
# ============================================================
PARAMS_2025 = TaxYearParams(
    year=2025,
    # ESt-Tarif
    grundfreibetrag=12_096,
    zone2_upper=17_443,
    zone2_offset=12_096,
    zone2_a=932.30,
    zone2_b=1_400.00,
    zone3_upper=68_480,
    zone3_offset=17_443,
    zone3_a=176.64,
    zone3_b=2_397.00,
    zone3_constant=1_015.13,
    zone4_upper=277_825,
    zone4_rate=0.42,
    zone4_offset=10_911.92,
    zone5_rate=0.45,
    zone5_offset=19_246.67,
    # Soli
    soli_freigrenze_single=19_950,
    soli_freigrenze_couple=39_900,
    # KV
    kv_zusatzbeitrag_avg=0.025,
    kv_bbg_annual=66_150,
    # RV
    rv_bbg_annual=96_600,
    # AV
    av_bbg_annual=96_600,
    # PV
    pv_rate_base=0.036,
    pv_bbg_annual=66_150,
    # Versicherungspflichtgrenze
    versicherungspflichtgrenze_annual=73_800,
    # Kindergeld & Kinderfreibetrag
    kindergeld_per_child_monthly=255.0,
    kinderfreibetrag_couple=9_600.0,
)

# ============================================================
# 2026
# ============================================================
PARAMS_2026 = TaxYearParams(
    year=2026,
    # ESt-Tarif
    grundfreibetrag=12_348,
    zone2_upper=17_799,
    zone2_offset=12_348,
    zone2_a=914.51,
    zone2_b=1_400.00,
    zone3_upper=69_878,
    zone3_offset=17_799,
    zone3_a=173.10,
    zone3_b=2_397.00,
    zone3_constant=1_034.87,
    zone4_upper=277_825,
    zone4_rate=0.42,
    zone4_offset=11_135.63,
    zone5_rate=0.45,
    zone5_offset=19_470.38,
    # Soli
    soli_freigrenze_single=20_350,
    soli_freigrenze_couple=40_700,
    # KV
    kv_zusatzbeitrag_avg=0.029,
    kv_bbg_annual=69_750,
    # RV
    rv_bbg_annual=101_400,
    # AV
    av_bbg_annual=101_400,
    # PV
    pv_rate_base=0.036,
    pv_bbg_annual=69_750,
    # Versicherungspflichtgrenze
    versicherungspflichtgrenze_annual=77_400,
    # Kindergeld & Kinderfreibetrag
    kindergeld_per_child_monthly=259.0,
    kinderfreibetrag_couple=9_756.0,
)

# ============================================================
# Registry
# ============================================================
TAX_YEARS: Dict[int, TaxYearParams] = {
    2025: PARAMS_2025,
    2026: PARAMS_2026,
}


def get_params(year: int) -> TaxYearParams:
    """Parameter für ein Steuerjahr abrufen."""
    if year not in TAX_YEARS:
        raise ValueError(f"Steuerjahr {year} nicht unterstützt. Verfügbar: {list(TAX_YEARS.keys())}")
    return TAX_YEARS[year]


# Alle 16 Bundesländer
BUNDESLAENDER = [
    "Baden-Württemberg",
    "Bayern",
    "Berlin",
    "Brandenburg",
    "Bremen",
    "Hamburg",
    "Hessen",
    "Mecklenburg-Vorpommern",
    "Niedersachsen",
    "Nordrhein-Westfalen",
    "Rheinland-Pfalz",
    "Saarland",
    "Sachsen",
    "Sachsen-Anhalt",
    "Schleswig-Holstein",
    "Thüringen",
]
