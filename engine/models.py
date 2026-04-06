"""Pydantic-Datenmodelle für Ein- und Ausgaben."""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator

from .parameters import BUNDESLAENDER


class PartnerInput(BaseModel):
    """Eingabedaten für einen Ehepartner."""
    brutto_annual: float = Field(0.0, ge=0, description="Jährliches Bruttogehalt (inkl. 13./14. Gehalt, Boni)")
    anzahl_gehaelter: int = Field(12, ge=1, le=15, description="Anzahl Monatsgehälter pro Jahr (12, 13, 14...)")
    kirchensteuer: bool = Field(False, description="Kirchensteuerpflichtig?")
    is_beamter: bool = Field(False, description="Beamter?")
    is_pkv: bool = Field(False, description="Privat krankenversichert?")
    pkv_monthly: float = Field(0.0, ge=0, description="Monatlicher PKV-Beitrag (AN-Anteil)")
    kv_zusatzbeitrag: Optional[float] = Field(
        None, ge=0, le=0.1,
        description="Individueller KV-Zusatzbeitrag (z.B. 0.017 für 1,7%). None = Durchschnitt"
    )
    weitere_einkuenfte: float = Field(0.0, ge=0, description="Weitere jährliche Einkünfte")
    werbungskosten_ueber_pauschale: float = Field(
        0.0, ge=0, description="Werbungskosten über der Pauschale (1.230 EUR)"
    )
    elterngeld_monthly: float = Field(0.0, ge=0, description="Monatlicher Elterngeld-Betrag")
    elterngeld_months: int = Field(0, ge=0, le=24, description="Anzahl Monate Elterngeld")

    @property
    def brutto_monthly(self) -> float:
        """Reguläres monatliches Brutto (Jahresbrutto / 12)."""
        return self.brutto_annual / 12 if self.brutto_annual > 0 else 0.0

    @property
    def brutto_per_payslip(self) -> float:
        """Brutto pro Gehaltsabrechnung (Jahresbrutto / Anzahl Gehälter)."""
        return self.brutto_annual / self.anzahl_gehaelter if self.brutto_annual > 0 else 0.0


class HouseholdInput(BaseModel):
    """Eingabedaten für den gesamten Haushalt."""
    partner1: PartnerInput
    partner2: PartnerInput
    year: int = Field(2026, ge=2025, le=2026)
    bundesland: str = Field("Bayern")
    kinder: int = Field(0, ge=0, le=10, description="Anzahl Kinder")

    @field_validator("bundesland")
    @classmethod
    def validate_bundesland(cls, v: str) -> str:
        if v not in BUNDESLAENDER:
            raise ValueError(f"Unbekanntes Bundesland: {v}. Verfügbar: {BUNDESLAENDER}")
        return v


class MonthlyResult(BaseModel):
    """Monatliches Netto-Ergebnis für einen Partner."""
    brutto: float
    lohnsteuer: float
    soli: float
    kirchensteuer: float
    kv_an: float
    rv_an: float
    av_an: float
    pv_an: float
    netto: float

    @property
    def total_sozialversicherung(self) -> float:
        return self.kv_an + self.rv_an + self.av_an + self.pv_an

    @property
    def total_steuern(self) -> float:
        return self.lohnsteuer + self.soli + self.kirchensteuer


class SteuerklasseResult(BaseModel):
    """Ergebnis für eine Steuerklassen-Kombination."""
    combo_label: str  # z.B. "3/5", "5/3", "4/4", "4+F/4+F"
    steuerklasse_p1: int
    steuerklasse_p2: int
    partner1_monthly: MonthlyResult
    partner2_monthly: MonthlyResult
    household_monthly_netto: float
    household_annual_netto: float
    # Jahresausgleich (Einkommensteuererklärung)
    annual_est_splitting: float      # Tatsächliche ESt via Splittingtabelle
    annual_soli_splitting: float     # Tatsächlicher Soli
    annual_kist_splitting: float     # Tatsächliche Kirchensteuer
    total_withheld_annual: float     # Summe einbehaltene LSt+Soli+KiSt über 12 Monate
    annual_difference: float         # Positiv = Erstattung, Negativ = Nachzahlung
    faktor: Optional[float] = None   # Nur für 4+Faktor


class ComparisonResult(BaseModel):
    """Gesamtvergleich aller Steuerklassen-Kombinationen."""
    household: HouseholdInput
    results: List[SteuerklasseResult]
    annual_est_actual: float         # Tatsächliche Jahres-ESt (gleich für alle Kombis)
    annual_soli_actual: float
    annual_kist_actual: float
    kindergeld_annual: float         # Jährliches Kindergeld
    recommendation: str
