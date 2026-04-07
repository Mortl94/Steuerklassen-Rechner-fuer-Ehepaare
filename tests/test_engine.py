"""Tests für die Steuer-Engine.

Referenzwerte geprüft gegen:
- BMF-Steuerrechner (bmf-steuerrechner.de)
- finanz-tools.de Einkommensteuer-Rechner
- Offizielle §32a EStG Formeln
"""

import pytest
from engine.parameters import get_params, PARAMS_2025, PARAMS_2026
from engine.tax import (
    calc_est, calc_est_splitting, calc_soli, calc_kirchensteuer,
    calc_est_with_progressionsvorbehalt,
)
from engine.social import calc_social_contributions, calc_pv_employee_rate
from engine.payroll import calc_monthly_netto, calc_faktor, calc_annual_lohnsteuer
from engine.models import PartnerInput, HouseholdInput, ElterngeldTyp
from engine.comparison import compare_steuerklassen


# ============================================================
# ESt-Formel Tests (§32a EStG)
# ============================================================

class TestESt2025:
    params = PARAMS_2025

    def test_zone1_zero(self):
        """Einkommen unter Grundfreibetrag -> 0 EUR Steuer."""
        assert calc_est(10_000, self.params) == 0
        assert calc_est(12_096, self.params) == 0

    def test_zone1_boundary(self):
        """Genau am Grundfreibetrag."""
        assert calc_est(12_096, self.params) == 0

    def test_zone2(self):
        """Zone 2: 12.097 - 17.443 EUR."""
        est = calc_est(15_000, self.params)
        assert est > 0
        # y = (15000 - 12096) / 10000 = 0.2904
        # est = (932.30 * 0.2904 + 1400) * 0.2904
        y = (15_000 - 12_096) / 10_000
        expected = int((932.30 * y + 1400) * y)
        assert est == expected

    def test_zone3(self):
        """Zone 3: 17.444 - 68.480 EUR."""
        est = calc_est(40_000, self.params)
        z = (40_000 - 17_443) / 10_000
        expected = int((176.64 * z + 2397) * z + 1015.13)
        assert est == expected

    def test_zone4(self):
        """Zone 4: Spitzensteuersatz 42%."""
        est = calc_est(100_000, self.params)
        expected = int(0.42 * 100_000 - 10_911.92)
        assert est == expected

    def test_zone5(self):
        """Zone 5: Reichensteuer 45%."""
        est = calc_est(300_000, self.params)
        expected = int(0.45 * 300_000 - 19_246.67)
        assert est == expected

    def test_negative_income(self):
        """Negatives Einkommen -> 0."""
        assert calc_est(-5_000, self.params) == 0

    def test_zone2_upper_boundary(self):
        """Obere Grenze Zone 2."""
        est = calc_est(17_443, self.params)
        y = (17_443 - 12_096) / 10_000
        expected = int((932.30 * y + 1400) * y)
        assert est == expected


class TestESt2026:
    params = PARAMS_2026

    def test_zone1(self):
        assert calc_est(12_348, self.params) == 0
        assert calc_est(12_000, self.params) == 0

    def test_zone2(self):
        est = calc_est(15_000, self.params)
        y = (15_000 - 12_348) / 10_000
        expected = int((914.51 * y + 1400) * y)
        assert est == expected

    def test_zone4(self):
        est = calc_est(100_000, self.params)
        expected = int(0.42 * 100_000 - 11_135.63)
        assert est == expected

    def test_zone5(self):
        est = calc_est(300_000, self.params)
        expected = int(0.45 * 300_000 - 19_470.38)
        assert est == expected


class TestSplitting:
    params = PARAMS_2025

    def test_splitting_less_than_individual(self):
        """Splitting-Tarif ist immer günstiger bei ungleichem Einkommen."""
        individual = calc_est(80_000, self.params)
        splitting = calc_est_splitting(80_000, self.params)
        assert splitting < individual

    def test_splitting_equal_income(self):
        """Bei gleichen Einkommen: Splitting = 2 * Grundtabelle(Hälfte)."""
        combined = 80_000
        splitting = calc_est_splitting(combined, self.params)
        individual_half = calc_est(40_000, self.params)
        assert splitting == 2 * individual_half

    def test_splitting_zero(self):
        """Unter doppeltem Grundfreibetrag -> 0."""
        assert calc_est_splitting(20_000, self.params) == 0


# ============================================================
# Solidaritätszuschlag Tests
# ============================================================

class TestSoli:
    params = PARAMS_2025

    def test_below_freigrenze(self):
        """EST unter Freigrenze -> kein Soli."""
        assert calc_soli(15_000, self.params) == 0.0
        assert calc_soli(19_950, self.params) == 0.0

    def test_above_freigrenze_milderung(self):
        """Knapp über Freigrenze -> Milderungszone."""
        est = 21_000
        soli = calc_soli(est, self.params)
        full = est * 0.055
        milderung = (est - 19_950) * 0.119
        assert soli == pytest.approx(min(full, milderung), abs=0.01)

    def test_full_soli(self):
        """Weit über Freigrenze -> voller Soli."""
        est = 50_000
        soli = calc_soli(est, self.params)
        # Bei 50.000: Milderung = (50000-19950)*0.119 = 3575.95
        # Voll = 50000 * 0.055 = 2750
        # min(2750, 3575.95) = 2750
        assert soli == pytest.approx(2_750.0, abs=0.01)

    def test_couple_freigrenze(self):
        """Paar-Freigrenze ist doppelt."""
        assert calc_soli(35_000, self.params, is_couple=True) == 0.0
        assert calc_soli(39_900, self.params, is_couple=True) == 0.0


# ============================================================
# Kirchensteuer Tests
# ============================================================

class TestKirchensteuer:
    params = PARAMS_2025

    def test_bayern(self):
        """Bayern: 8%."""
        kist = calc_kirchensteuer(10_000, "Bayern", self.params)
        assert kist == pytest.approx(800.0, abs=0.01)

    def test_bw(self):
        """Baden-Württemberg: 8%."""
        kist = calc_kirchensteuer(10_000, "Baden-Württemberg", self.params)
        assert kist == pytest.approx(800.0, abs=0.01)

    def test_nrw(self):
        """NRW: 9%."""
        kist = calc_kirchensteuer(10_000, "Nordrhein-Westfalen", self.params)
        assert kist == pytest.approx(900.0, abs=0.01)

    def test_zero(self):
        """Keine ESt -> keine KiSt."""
        assert calc_kirchensteuer(0, "Bayern", self.params) == 0.0


# ============================================================
# Sozialversicherung Tests
# ============================================================

class TestSocialContributions:
    params = PARAMS_2025

    def test_standard_employee(self):
        """Standard-Arbeitnehmer mit 4.000 EUR Brutto."""
        sv = calc_social_contributions(4_000, self.params, kinder=0)
        assert sv.kv_an > 0
        assert sv.rv_an > 0
        assert sv.av_an > 0
        assert sv.pv_an > 0
        assert sv.total_an > 0

    def test_bbg_capping_kv(self):
        """KV-Beitrag wird bei BBG gedeckelt."""
        brutto_high = 10_000  # über BBG
        sv = calc_social_contributions(brutto_high, self.params, kinder=1)
        kv_bbg_monthly = self.params.kv_bbg_annual / 12
        kv_rate = (self.params.kv_general_rate + self.params.kv_zusatzbeitrag_avg) / 2
        max_kv = round(kv_bbg_monthly * kv_rate, 2)
        assert sv.kv_an == max_kv

    def test_beamter(self):
        """Beamter: keine SV-Beiträge (außer PKV)."""
        sv = calc_social_contributions(
            5_000, self.params, kinder=0,
            is_beamter=True, is_pkv=True, pkv_monthly=350,
        )
        assert sv.rv_an == 0
        assert sv.av_an == 0
        assert sv.pv_an == 0
        assert sv.kv_an == 350  # PKV-Beitrag

    def test_pv_kinderlos(self):
        """Kinderloser: höherer PV-Beitrag."""
        sv_0 = calc_social_contributions(4_000, self.params, kinder=0)
        sv_1 = calc_social_contributions(4_000, self.params, kinder=1)
        assert sv_0.pv_an > sv_1.pv_an


class TestPVRate:
    params = PARAMS_2025

    def test_kinderlos(self):
        rate = calc_pv_employee_rate(self.params, kinder=0)
        expected = self.params.pv_rate_base / 2 + self.params.pv_kinderlos_zuschlag
        assert rate == pytest.approx(expected)

    def test_1_kind(self):
        rate = calc_pv_employee_rate(self.params, kinder=1)
        assert rate == pytest.approx(self.params.pv_rate_base / 2)

    def test_2_kinder(self):
        rate = calc_pv_employee_rate(self.params, kinder=2)
        expected = self.params.pv_rate_base / 2 - self.params.pv_kind_abschlag
        assert rate == pytest.approx(expected)

    def test_5_kinder(self):
        rate = calc_pv_employee_rate(self.params, kinder=5)
        expected = self.params.pv_rate_base / 2 - 4 * self.params.pv_kind_abschlag
        assert rate == pytest.approx(expected)


# ============================================================
# Payroll / Lohnsteuer Tests
# ============================================================

class TestPayroll:
    params = PARAMS_2025

    def test_monthly_netto_positive(self):
        """Netto muss positiv sein."""
        result = calc_monthly_netto(
            4_000, 4, self.params, bundesland="Bayern",
        )
        assert result.netto > 0
        assert result.netto < result.brutto

    def test_sk3_more_netto_than_sk4(self):
        """SK 3 -> mehr Netto als SK 4 (monatlich)."""
        r3 = calc_monthly_netto(5_000, 3, self.params)
        r4 = calc_monthly_netto(5_000, 4, self.params)
        assert r3.netto > r4.netto

    def test_sk5_less_netto_than_sk4(self):
        """SK 5 -> weniger Netto als SK 4 (monatlich)."""
        r5 = calc_monthly_netto(3_000, 5, self.params)
        r4 = calc_monthly_netto(3_000, 4, self.params)
        assert r5.netto < r4.netto

    def test_components_sum_to_brutto(self):
        """Alle Abzüge + Netto = Brutto."""
        r = calc_monthly_netto(5_000, 4, self.params, kirchensteuer=True, bundesland="Bayern")
        total = (r.lohnsteuer + r.soli + r.kirchensteuer
                 + r.kv_an + r.rv_an + r.av_an + r.pv_an + r.netto)
        assert total == pytest.approx(r.brutto, abs=0.02)

    def test_payroll_periods_distribute_annual_tax(self):
        """Bei 13 Gehältern wird die Jahressteuer auf 13 Abrechnungen verteilt."""
        r12 = calc_monthly_netto(
            60_000 / 12, 4, self.params,
            brutto_annual=60_000,
            payroll_periods=12,
        )
        r13 = calc_monthly_netto(
            60_000 / 13, 4, self.params,
            brutto_annual=60_000,
            payroll_periods=13,
        )

        assert r13.brutto == pytest.approx(60_000 / 13)
        assert r13.total_steuern < r12.total_steuern
        assert r13.total_steuern * 13 == pytest.approx(r12.total_steuern * 12, abs=1.0)


class TestFaktor:
    params = PARAMS_2025

    def test_faktor_less_than_one(self):
        """Faktor muss <= 1.0 sein."""
        f = calc_faktor(60_000, 40_000, self.params)
        assert 0 < f <= 1.0

    def test_equal_income_faktor(self):
        """Bei gleichen Einkommen ist der Faktor nah an 1.0."""
        f = calc_faktor(50_000, 50_000, self.params)
        assert 0.9 < f <= 1.0

    def test_unequal_income_lower_faktor(self):
        """Bei ungleichem Einkommen ist der Faktor kleiner."""
        f_equal = calc_faktor(50_000, 50_000, self.params)
        f_unequal = calc_faktor(80_000, 20_000, self.params)
        assert f_unequal < f_equal


# ============================================================
# Integration: Vergleich Steuerklassen
# ============================================================

class TestComparison:

    def _make_household(self, brutto1=60_000, brutto2=36_000, year=2025):
        return HouseholdInput(
            partner1=PartnerInput(brutto_annual=brutto1),
            partner2=PartnerInput(brutto_annual=brutto2),
            year=year,
            bundesland="Bayern",
            kinder=0,
        )

    def test_four_combinations(self):
        """Es werden genau 4 Steuerklassen-Kombinationen berechnet."""
        result = compare_steuerklassen(self._make_household())
        assert len(result.results) == 4

    def test_same_annual_est(self):
        """Alle Kombinationen haben die gleiche tatsächliche Jahres-ESt."""
        result = compare_steuerklassen(self._make_household())
        est_values = [r.annual_est_splitting for r in result.results]
        assert all(e == est_values[0] for e in est_values)

    def test_effective_annual_same(self):
        """Nach Steuererklärung ist das effektive Jahresergebnis gleich."""
        result = compare_steuerklassen(self._make_household())
        effective = [
            r.household_annual_netto + r.annual_difference
            for r in result.results
        ]
        # Alle sollten (nahezu) gleich sein
        for e in effective:
            assert e == pytest.approx(effective[0], abs=5.0)

    def test_sk35_highest_monthly(self):
        """SK 3/5 hat typischerweise das höchste Haushalts-Netto wenn P1 mehr verdient."""
        result = compare_steuerklassen(self._make_household(brutto1=72_000, brutto2=24_000))
        sk35 = result.results[0]  # 3/5
        sk44 = result.results[2]  # 4/4
        assert sk35.household_monthly_netto >= sk44.household_monthly_netto

    def test_with_children(self):
        """Berechnung mit Kindern funktioniert."""
        hh = HouseholdInput(
            partner1=PartnerInput(brutto_annual=60_000),
            partner2=PartnerInput(brutto_annual=36_000),
            year=2025,
            bundesland="Bayern",
            kinder=2,
        )
        result = compare_steuerklassen(hh)
        assert result.kindergeld_annual == 2 * 255 * 12

    def test_year_2026(self):
        """Berechnung für 2026 funktioniert."""
        result = compare_steuerklassen(self._make_household(year=2026))
        assert len(result.results) == 4

    def test_beamter(self):
        """Berechnung mit Beamtem funktioniert."""
        hh = HouseholdInput(
            partner1=PartnerInput(
                brutto_annual=60_000, is_beamter=True,
                is_pkv=True, pkv_monthly=350,
            ),
            partner2=PartnerInput(brutto_annual=36_000),
            year=2025,
            bundesland="Bayern",
            kinder=0,
        )
        result = compare_steuerklassen(hh)
        # Beamter hat höheres Netto wegen fehlender SV
        sk44 = result.results[2]
        assert sk44.partner1_monthly.rv_an == 0
        assert sk44.partner1_monthly.av_an == 0

    def test_elterngeld_only(self):
        """Partner 2 hat nur Elterngeld, kein aktuelles Brutto."""
        hh = HouseholdInput(
            partner1=PartnerInput(brutto_annual=60_000),
            partner2=PartnerInput(
                brutto_annual=0,
                elterngeld_typ=ElterngeldTyp.PLUS,
                elterngeld_brutto_annual=48_000,
            ),
            year=2025,
            bundesland="Bayern",
            kinder=1,
        )
        result = compare_steuerklassen(hh)
        assert len(result.results) == 4
        # Partner 2 hat kein Brutto -> Netto = 0 (Elterngeld wird separat ausgezahlt)
        sk44 = result.results[2]
        assert sk44.partner2_monthly.netto == 0
        assert sk44.partner2_monthly.lohnsteuer == 0
        # Elterngeld wird aus dem Brutto vor der Geburt berechnet
        assert result.elterngeld_p2.elterngeld_monthly > 0
        assert result.elterngeld_p2.netto_vor_geburt > 0
        # Progressionsvorbehalt erhöht die Steuer auf Partner 1
        hh_no_eg = HouseholdInput(
            partner1=PartnerInput(brutto_annual=60_000),
            partner2=PartnerInput(brutto_annual=0),
            year=2025,
            bundesland="Bayern",
            kinder=1,
        )
        result_no_eg = compare_steuerklassen(hh_no_eg)
        assert result.annual_est_actual >= result_no_eg.annual_est_actual

    def test_elterngeld_separate_brutto(self):
        """Elterngeld-Brutto ist unabhängig vom aktuellen Brutto."""
        hh = HouseholdInput(
            partner1=PartnerInput(brutto_annual=60_000),
            partner2=PartnerInput(
                brutto_annual=30_000,
                elterngeld_typ=ElterngeldTyp.BASIS,
                elterngeld_brutto_annual=50_000,
            ),
            year=2025,
            bundesland="Bayern",
            kinder=1,
        )
        result = compare_steuerklassen(hh)
        # Elterngeld basiert auf 50k, nicht auf 30k
        # Partner 2 hat Netto aus dem aktuellen 30k Brutto
        sk44 = result.results[2]
        assert sk44.partner2_monthly.netto > 0
        # Elterngeld-Netto basiert auf 50k Brutto vor Geburt
        assert result.elterngeld_p2.elterngeld_monthly > 300  # über Mindestbetrag
        assert result.elterngeld_p2.netto_vor_geburt > 0

    def test_13_gehaelter(self):
        """13 Monatsgehälter: gleiche Jahressteuer wie 12 bei gleichem Jahresbrutto."""
        hh_12 = HouseholdInput(
            partner1=PartnerInput(brutto_annual=60_000, anzahl_gehaelter=12),
            partner2=PartnerInput(brutto_annual=36_000, anzahl_gehaelter=12),
            year=2025, bundesland="Bayern", kinder=0,
        )
        hh_13 = HouseholdInput(
            partner1=PartnerInput(brutto_annual=60_000, anzahl_gehaelter=13),
            partner2=PartnerInput(brutto_annual=36_000, anzahl_gehaelter=13),
            year=2025, bundesland="Bayern", kinder=0,
        )
        r12 = compare_steuerklassen(hh_12)
        r13 = compare_steuerklassen(hh_13)
        # Gleiche Jahressteuer (Jahresbrutto ist identisch)
        assert r12.annual_est_actual == r13.annual_est_actual
        # brutto_monthly ist jetzt Payslip-Betrag
        assert hh_12.partner1.brutto_monthly == 5000
        assert hh_13.partner1.brutto_monthly == pytest.approx(60_000 / 13)
        # brutto_monthly_avg ist immer brutto_annual / 12
        assert hh_12.partner1.brutto_monthly_avg == 5000
        assert hh_13.partner1.brutto_monthly_avg == 5000
        # Monatliches Netto bei 13 Gehältern ist niedriger (niedrigeres Payslip-Brutto)
        sk44_12 = r12.results[2]
        sk44_13 = r13.results[2]
        assert sk44_13.partner1_monthly.brutto < sk44_12.partner1_monthly.brutto
        assert sk44_13.partner1_monthly.total_steuern < sk44_12.partner1_monthly.total_steuern
        assert sk44_13.total_withheld_annual == pytest.approx(
            sk44_12.total_withheld_annual, abs=1.0
        )
        # Aber Jahres-Netto ist gleich (gleiches brutto_annual)
        assert sk44_12.household_annual_netto == pytest.approx(
            sk44_13.household_annual_netto, abs=1.0
        )
