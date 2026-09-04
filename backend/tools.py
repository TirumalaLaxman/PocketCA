"""
PocketCA - Financial Calculation Tools & Calculators
Provides deterministic, audit-ready Indian CA financial calculations for:
- Goods & Services Tax (GST)
- Income Tax (New vs Old Regime comparison under FY 2024-25 & FY 2025-26)
- Tax Deducted at Source (TDS) under Income Tax Act 1961
- Depreciation (Straight Line Method & Written Down Value)
- Loan EMI & Amortization
- House Rent Allowance (HRA) Exemption u/s 10(13A)
- Double-Entry Journal Entry Generation
"""

from typing import Dict, Any, List, Optional
import math


def calculate_gst(
    amount: float,
    rate: float,
    tax_type: str = "exclusive",
    is_interstate: bool = False
) -> Dict[str, Any]:
    """
    Calculate GST for inclusive or exclusive amounts with CGST/SGST or IGST breakdown.
    rate: e.g. 5, 12, 18, 28
    tax_type: 'exclusive' or 'inclusive'
    is_interstate: True for IGST, False for CGST + SGST
    """
    amount = float(amount)
    rate = float(rate)
    
    if tax_type.lower() == "inclusive":
        taxable_value = amount / (1.0 + (rate / 100.0))
        total_gst = amount - taxable_value
        total_amount = amount
    else:  # exclusive
        taxable_value = amount
        total_gst = amount * (rate / 100.0)
        total_amount = amount + total_gst

    taxable_value = round(taxable_value, 2)
    total_gst = round(total_gst, 2)
    total_amount = round(total_amount, 2)

    if is_interstate:
        igst = total_gst
        cgst = 0.0
        sgst = 0.0
        tax_split = f"IGST ({rate}%): ₹{igst:,.2f}"
    else:
        half_rate = rate / 2.0
        cgst = round(total_gst / 2.0, 2)
        sgst = round(total_gst - cgst, 2)
        igst = 0.0
        tax_split = f"CGST ({half_rate}%): ₹{cgst:,.2f} + SGST ({half_rate}%): ₹{sgst:,.2f}"

    return {
        "success": True,
        "input_amount": amount,
        "rate_percent": rate,
        "tax_type": tax_type.capitalize(),
        "is_interstate": is_interstate,
        "taxable_value": taxable_value,
        "total_gst": total_gst,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "total_amount": total_amount,
        "tax_split": tax_split,
        "summary": (
            f"Taxable Value: ₹{taxable_value:,.2f} | "
            f"GST ({rate}%): ₹{total_gst:,.2f} ({tax_split}) | "
            f"Total Invoice Amount: ₹{total_amount:,.2f}"
        )
    }


def calculate_income_tax(
    gross_income: float,
    financial_year: str = "2024-25",
    deductions_80c: float = 0.0,
    deductions_80d: float = 0.0,
    other_deductions: float = 0.0,
    is_senior_citizen: bool = False,
    is_super_senior: bool = False
) -> Dict[str, Any]:
    """
    Compare and compute Income Tax liability for Individual under New Tax Regime (Sec 115BAC)
    vs Old Tax Regime for FY 2024-25 / FY 2025-26.
    Includes Standard Deduction (₹75k New / ₹50k Old), Section 87A rebate, and 4% Health & Ed Cess.
    """
    gross_income = float(gross_income)
    deductions_80c = min(float(deductions_80c), 150000.0)
    deductions_80d = float(deductions_80d)
    other_deductions = float(other_deductions)

    # 1. NEW TAX REGIME (Sec 115BAC - Budget 2024 amendments)
    std_deduction_new = 75000.0
    taxable_new = max(0.0, gross_income - std_deduction_new)

    tax_new_slabs = 0.0
    breakdown_new = []

    if taxable_new > 1500000:
        slab_tax = (taxable_new - 1500000) * 0.30
        tax_new_slabs += slab_tax
        breakdown_new.append(f"> ₹15L @ 30%: ₹{slab_tax:,.2f}")
    if taxable_new > 1200000:
        slab_tax = (min(taxable_new, 1500000) - 1200000) * 0.20
        tax_new_slabs += slab_tax
        breakdown_new.append(f"₹12L - ₹15L @ 20%: ₹{slab_tax:,.2f}")
    if taxable_new > 1000000:
        slab_tax = (min(taxable_new, 1200000) - 1000000) * 0.15
        tax_new_slabs += slab_tax
        breakdown_new.append(f"₹10L - ₹12L @ 15%: ₹{slab_tax:,.2f}")
    if taxable_new > 700000:
        slab_tax = (min(taxable_new, 1000000) - 700000) * 0.10
        tax_new_slabs += slab_tax
        breakdown_new.append(f"₹7L - ₹10L @ 10%: ₹{slab_tax:,.2f}")
    if taxable_new > 300000:
        slab_tax = (min(taxable_new, 700000) - 300000) * 0.05
        tax_new_slabs += slab_tax
        breakdown_new.append(f"₹3L - ₹7L @ 5%: ₹{slab_tax:,.2f}")

    rebate_new = 0.0
    if taxable_new <= 700000:
        rebate_new = tax_new_slabs
        tax_after_rebate_new = 0.0
    else:
        excess_income = taxable_new - 700000
        if tax_new_slabs > excess_income:
            marginal_relief = tax_new_slabs - excess_income
            rebate_new = marginal_relief
            tax_after_rebate_new = excess_income
        else:
            tax_after_rebate_new = tax_new_slabs

    cess_new = round(tax_after_rebate_new * 0.04, 2)
    total_tax_new = round(tax_after_rebate_new + cess_new, 2)

    # 2. OLD TAX REGIME
    std_deduction_old = 50000.0
    total_old_deductions = std_deduction_old + deductions_80c + deductions_80d + other_deductions
    taxable_old = max(0.0, gross_income - total_old_deductions)

    exempt_limit = 500000.0 if is_super_senior else (300000.0 if is_senior_citizen else 250000.0)

    tax_old_slabs = 0.0
    breakdown_old = []

    if taxable_old > 1000000:
        slab_tax = (taxable_old - 1000000) * 0.30
        tax_old_slabs += slab_tax
        breakdown_old.append(f"> ₹10L @ 30%: ₹{slab_tax:,.2f}")
    if taxable_old > 500000:
        slab_tax = (min(taxable_old, 1000000) - 500000) * 0.20
        tax_old_slabs += slab_tax
        breakdown_old.append(f"₹5L - ₹10L @ 20%: ₹{slab_tax:,.2f}")
    if taxable_old > exempt_limit:
        slab_tax = (min(taxable_old, 500000) - exempt_limit) * 0.05
        tax_old_slabs += slab_tax
        breakdown_old.append(f"₹{exempt_limit/100000:g}L - ₹5L @ 5%: ₹{slab_tax:,.2f}")

    rebate_old = 0.0
    if taxable_old <= 500000:
        rebate_old = min(tax_old_slabs, 12500.0)
        tax_after_rebate_old = max(0.0, tax_old_slabs - rebate_old)
    else:
        tax_after_rebate_old = tax_old_slabs

    cess_old = round(tax_after_rebate_old * 0.04, 2)
    total_tax_old = round(tax_after_rebate_old + cess_old, 2)

    tax_diff = abs(total_tax_old - total_tax_new)
    if total_tax_new < total_tax_old:
        recommended = "New Tax Regime"
        savings_text = f"You save ₹{tax_diff:,.2f} under the New Tax Regime!"
    elif total_tax_old < total_tax_new:
        recommended = "Old Tax Regime"
        savings_text = f"You save ₹{tax_diff:,.2f} under the Old Tax Regime!"
    else:
        recommended = "Either (Same Tax)"
        savings_text = "Both tax regimes yield the exact same tax liability."

    return {
        "success": True,
        "gross_income": gross_income,
        "financial_year": financial_year,
        "new_regime": {
            "regime_name": "New Tax Regime (Section 115BAC)",
            "standard_deduction": std_deduction_new,
            "net_taxable_income": taxable_new,
            "base_tax": round(tax_new_slabs, 2),
            "rebate_87a": round(rebate_new, 2),
            "cess_4_percent": cess_new,
            "total_tax_payable": total_tax_new,
            "breakdown": breakdown_new
        },
        "old_regime": {
            "regime_name": "Old Tax Regime",
            "standard_deduction": std_deduction_old,
            "deductions_80c": deductions_80c,
            "deductions_80d": deductions_80d,
            "other_deductions": other_deductions,
            "total_deductions": total_old_deductions,
            "net_taxable_income": taxable_old,
            "base_tax": round(tax_old_slabs, 2),
            "rebate_87a": round(rebate_old, 2),
            "cess_4_percent": cess_old,
            "total_tax_payable": total_tax_old,
            "breakdown": breakdown_old
        },
        "recommendation": {
            "optimal_regime": recommended,
            "savings": round(tax_diff, 2),
            "summary": savings_text
        }
    }


def calculate_tds(
    section: str,
    amount: float,
    pan_available: bool = True,
    payee_type: str = "individual"
) -> Dict[str, Any]:
    """
    Calculate Tax Deducted at Source (TDS) under Income Tax Act 1961.
    Supported Sections: 194C, 194J, 194I, 194H, 194Q, 194A.
    Applies Section 206AA (20% rate) if PAN is missing.
    """
    amount = float(amount)
    sec_clean = section.upper().replace("SECTION", "").replace("SEC", "").strip()

    rules: Dict[str, Dict[str, Any]] = {
        "194C": {
            "title": "Payments to Contractors / Subcontractors",
            "rate_individual": 1.0,
            "rate_company": 2.0,
            "single_threshold": 30000.0,
            "aggregate_threshold": 100000.0,
            "desc": "1% for Individual/HUF, 2% for Others. Threshold: ₹30,000 single bill or ₹1,00,000 aggregate/year."
        },
        "194J": {
            "title": "Fees for Professional / Technical Services",
            "rate_professional": 10.0,
            "rate_technical": 2.0,
            "threshold": 30000.0,
            "desc": "10% for professional services; 2% for technical/royalty/call center. Threshold: ₹30,000/year."
        },
        "194I": {
            "title": "Rent on Land, Building or Machinery",
            "rate_machinery": 2.0,
            "rate_land_building": 10.0,
            "threshold": 240000.0,
            "desc": "2% on Plant/Machinery/Equipment; 10% on Land/Building/Furniture. Threshold: ₹2,40,000/year."
        },
        "194H": {
            "title": "Commission or Brokerage",
            "rate": 2.0,
            "threshold": 15000.0,
            "desc": "2% on commission or brokerage exceeding ₹15,000 per financial year."
        },
        "194Q": {
            "title": "Purchase of Goods by Buyers with Turnover > ₹10 Cr",
            "rate": 0.1,
            "threshold": 5000000.0,
            "desc": "0.1% on purchase value exceeding ₹50,00,000 from a resident seller."
        },
        "194A": {
            "title": "Interest other than Interest on Securities (FD/Deposits)",
            "rate": 10.0,
            "threshold": 40000.0,
            "desc": "10% on bank interest exceeding ₹40,000 (₹50,000 for Senior Citizens) or ₹5,000 for others."
        }
    }

    matched_sec = None
    for k in rules:
        if k in sec_clean:
            matched_sec = k
            break

    if not matched_sec:
        matched_sec = "194J"

    rule = rules[matched_sec]
    threshold = rule.get("threshold", rule.get("single_threshold", 0.0))
    is_threshold_exceeded = amount > threshold

    if matched_sec == "194C":
        base_rate = rule["rate_individual"] if "indiv" in payee_type.lower() or "huf" in payee_type.lower() else rule["rate_company"]
    elif matched_sec == "194J":
        base_rate = rule["rate_technical"] if "tech" in payee_type.lower() else rule["rate_professional"]
    elif matched_sec == "194I":
        base_rate = rule["rate_machinery"] if "machine" in payee_type.lower() or "plant" in payee_type.lower() else rule["rate_land_building"]
    else:
        base_rate = rule.get("rate", 10.0)

    if not pan_available:
        applied_rate = max(base_rate, 20.0)
        pan_note = "Higher rate of 20% applied under Section 206AA as PAN is unavailable."
    else:
        applied_rate = base_rate
        pan_note = "Valid PAN furnished. Regular statutory rate applied."

    if matched_sec == "194Q":
        taxable_amount = max(0.0, amount - 5000000.0)
    else:
        taxable_amount = amount

    tds_amount = round(taxable_amount * (applied_rate / 100.0), 2)
    net_payable = round(amount - tds_amount, 2)

    return {
        "success": True,
        "section": f"Section {matched_sec}",
        "title": rule["title"],
        "bill_amount": amount,
        "taxable_amount": taxable_amount,
        "threshold": threshold,
        "is_threshold_exceeded": is_threshold_exceeded,
        "pan_available": pan_available,
        "applied_rate_percent": applied_rate,
        "tds_amount": tds_amount,
        "net_payable": net_payable,
        "pan_note": pan_note,
        "summary": (
            f"Bill Amount: ₹{amount:,.2f} | Section {matched_sec} ({applied_rate}%) | "
            f"TDS to Deduct: ₹{tds_amount:,.2f} | Net Payable to Vendor: ₹{net_payable:,.2f}"
        )
    }


def calculate_depreciation(
    cost: float,
    salvage_value: float = 0.0,
    useful_life_years: int = 5,
    method: str = "SLM",
    rate_percent: Optional[float] = None
) -> Dict[str, Any]:
    """
    Calculate asset depreciation schedule under Straight Line Method (SLM)
    or Written Down Value (WDV) method.
    """
    cost = float(cost)
    salvage_value = float(salvage_value)
    useful_life_years = max(1, int(useful_life_years))
    method = method.upper()

    schedule = []
    current_book_value = cost

    if method == "SLM":
        annual_dep = round((cost - salvage_value) / useful_life_years, 2)
        effective_rate = round((annual_dep / cost) * 100.0, 2) if cost > 0 else 0.0

        for year in range(1, useful_life_years + 1):
            opening = current_book_value
            dep_charge = min(annual_dep, max(0.0, opening - salvage_value))
            closing = round(opening - dep_charge, 2)
            schedule.append({
                "year": year,
                "opening_value": opening,
                "depreciation_charge": dep_charge,
                "closing_value": closing
            })
            current_book_value = closing
    else:  # WDV
        if rate_percent is not None and rate_percent > 0:
            wdv_rate = float(rate_percent)
        else:
            if cost > 0 and salvage_value > 0 and salvage_value < cost:
                wdv_rate = round((1.0 - math.pow(salvage_value / cost, 1.0 / useful_life_years)) * 100.0, 2)
            else:
                wdv_rate = 15.0

        effective_rate = wdv_rate
        for year in range(1, useful_life_years + 1):
            opening = current_book_value
            dep_charge = round(opening * (wdv_rate / 100.0), 2)
            closing = round(max(salvage_value, opening - dep_charge), 2)
            schedule.append({
                "year": year,
                "opening_value": opening,
                "depreciation_charge": dep_charge,
                "closing_value": closing
            })
            current_book_value = closing

    total_dep = round(cost - current_book_value, 2)

    return {
        "success": True,
        "initial_cost": cost,
        "salvage_value": salvage_value,
        "useful_life_years": useful_life_years,
        "method": method,
        "effective_rate_percent": effective_rate,
        "total_depreciation": total_dep,
        "final_book_value": current_book_value,
        "schedule": schedule,
        "summary": (
            f"Asset Cost: ₹{cost:,.2f} | Method: {method} ({effective_rate}%) | "
            f"Total Depreciation over {useful_life_years} years: ₹{total_dep:,.2f} | "
            f"Remaining Book Value: ₹{current_book_value:,.2f}"
        )
    }


def calculate_emi(
    principal: float,
    annual_rate: float,
    tenure_months: int
) -> Dict[str, Any]:
    """
    Calculate Monthly Loan EMI, total interest, and repayment amount.
    """
    principal = float(principal)
    annual_rate = float(annual_rate)
    tenure_months = int(tenure_months)

    if principal <= 0 or annual_rate <= 0 or tenure_months <= 0:
        return {"success": False, "error": "Principal, rate, and tenure must be positive numbers."}

    monthly_rate = (annual_rate / 12.0) / 100.0
    factor = math.pow(1.0 + monthly_rate, tenure_months)
    emi = round(principal * monthly_rate * factor / (factor - 1.0), 2)

    total_payment = round(emi * tenure_months, 2)
    total_interest = round(total_payment - principal, 2)

    return {
        "success": True,
        "principal_loan_amount": principal,
        "annual_interest_rate": annual_rate,
        "tenure_months": tenure_months,
        "tenure_years": round(tenure_months / 12.0, 1),
        "monthly_emi": emi,
        "total_interest_payable": total_interest,
        "total_amount_payable": total_payment,
        "summary": (
            f"Loan Principal: ₹{principal:,.2f} | Rate: {annual_rate}% p.a. | "
            f"Monthly EMI: ₹{emi:,.2f} | Total Interest: ₹{total_interest:,.2f} | "
            f"Total Repayment: ₹{total_payment:,.2f}"
        )
    }


def calculate_hra_exemption(
    basic_salary: float,
    da: float = 0.0,
    hra_received: float = 0.0,
    rent_paid: float = 0.0,
    is_metro: bool = False
) -> Dict[str, Any]:
    """
    Calculate House Rent Allowance (HRA) Exemption under Section 10(13A) of Income Tax Act 1961.
    """
    salary = float(basic_salary) + float(da)
    hra_received = float(hra_received)
    rent_paid = float(rent_paid)

    cond1 = hra_received
    cond2 = max(0.0, rent_paid - (0.10 * salary))
    cond3 = (0.50 * salary) if is_metro else (0.40 * salary)

    exempt_hra = round(min(cond1, cond2, cond3), 2)
    taxable_hra = round(max(0.0, hra_received - exempt_hra), 2)

    return {
        "success": True,
        "annual_salary_basic_da": salary,
        "actual_hra_received": hra_received,
        "annual_rent_paid": rent_paid,
        "is_metro": is_metro,
        "condition_1_actual_hra": cond1,
        "condition_2_rent_minus_10pct_salary": round(cond2, 2),
        "condition_3_salary_percentage": round(cond3, 2),
        "exempt_hra": exempt_hra,
        "taxable_hra": taxable_hra,
        "summary": (
            f"HRA Received: ₹{hra_received:,.2f} | Section 10(13A) Exempt HRA: ₹{exempt_hra:,.2f} | "
            f"Taxable HRA to be added to Gross Salary: ₹{taxable_hra:,.2f}"
        )
    }


def generate_journal_entry(
    transaction_description: str,
    amount: float,
    debit_account: str,
    credit_account: str,
    narration: Optional[str] = None
) -> Dict[str, Any]:
    """
    Format standard double-entry bookkeeping journal entry with debit/credit accounts and narration.
    """
    amount = float(amount)
    if not narration:
        narration = f"Being transaction for {transaction_description.strip()} recorded."
    elif not narration.lower().startswith("being"):
        narration = f"Being {narration.strip()}"

    entry_text = (
        f"**Journal Entry:**\n\n"
        f"| Account Particulars | Debit (₹) | Credit (₹) |\n"
        f"| :--- | :--- | :--- |\n"
        f"| **{debit_account.strip()} A/c** ... Dr | {amount:,.2f} | - |\n"
        f"| &nbsp;&nbsp;&nbsp;&nbsp;To **{credit_account.strip()} A/c** | - | {amount:,.2f} |\n"
        f"| *(Narration: {narration})* | | |\n"
    )

    return {
        "success": True,
        "transaction": transaction_description,
        "amount": amount,
        "debit_account": debit_account,
        "credit_account": credit_account,
        "narration": narration,
        "formatted_markdown": entry_text
    }
