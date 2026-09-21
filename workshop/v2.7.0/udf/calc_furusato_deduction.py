# Optional Fabric User Data Function for the workshop.
# This is a mechanical illustration of the 2,000-yen annual self-payment rule.
# It does not calculate the taxpayer-specific deduction limit and is not tax
# advice. The Data Agent must present the result as "before the personal cap".

import fabric.functions as fn


udf = fn.UserDataFunctions()


@udf.function()
def calc_furusato_deduction(annualDonationAmountYen: int) -> dict:
    # Split annual donations into self-payment and amount before the cap.
    if annualDonationAmountYen < 0:
        raise ValueError("annualDonationAmountYen must be zero or greater.")

    annualSelfPaymentYen = min(annualDonationAmountYen, 2000)
    deductibleBeforePersonalCapYen = max(
        annualDonationAmountYen - annualSelfPaymentYen,
        0,
    )
    return {
        "annualDonationAmountYen": annualDonationAmountYen,
        "annualSelfPaymentYen": annualSelfPaymentYen,
        "deductibleBeforePersonalCapYen": deductibleBeforePersonalCapYen,
        "personalCapApplied": False,
    }
