K_ANONYMITY_THRESHOLD = 10

SENSITIVITY_TIERS: dict[str, float] = {
    "public": 0.00,
    "aggregated": 0.01,
    "sensitive": 0.05,
    "strategic": 0.25,
}
