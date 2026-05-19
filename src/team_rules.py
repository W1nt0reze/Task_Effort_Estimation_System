from __future__ import annotations

UDP_ALIASES = {"udp", "udp_ndd", "udp_core", "front_ndd"}

TEAM_TAGS = [
    "cargo_web",
    "courier_product",
    "united_dispatch",
    "cargo_b2b",
    "cargo_c2c",
    "dragon_infra",
    "cargo_pricing",
    "cargo_finance",
    "cargo_planned",
    "motion_model",
    "cargo_support",
    "udp",
]

TEAM_ALIASES = {team: team for team in TEAM_TAGS}
TEAM_ALIASES.update({alias: "udp" for alias in UDP_ALIASES})


def split_tags(raw: str | float | None) -> list[str]:
    if raw is None:
        return []

    text = str(raw).strip()
    if not text or text.lower() == "nan":
        return []

    return [part.strip().lower() for part in text.split(",") if part.strip()]


def extract_team(raw_tags: str | float | None, default: str = "other") -> str:
    """
    Извлекает команду из служебных меток Яндекс.Трекера.

    Командами считаются только заранее согласованные значения.
    udp, udp_ndd, udp_core и front_ndd объединяются в одну команду udp.
    Остальные метки, например ru, cis, int, complete, epic, не используются
    как командный признак.
    """
    tags = split_tags(raw_tags)

    for tag in tags:
        if tag in TEAM_ALIASES:
            return TEAM_ALIASES[tag]

    return default


def known_teams() -> list[str]:
    return TEAM_TAGS.copy()
