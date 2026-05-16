K_ANONYMITY_THRESHOLD = 10

DEFAULT_SENSITIVITY_TIER = "aggregated"

SENSITIVITY_TIERS: dict[str, float] = {
    "public": 0.00,
    "aggregated": 0.01,
    "sensitive": 0.05,
    "strategic": 0.25,
}

OUT_OF_SCOPE_RESPONSE = (
    "I can only answer aggregated business intelligence questions about registered "
    "companies (customers, shipments, clinical trials). Personal or general questions "
    "are outside this platform."
)
