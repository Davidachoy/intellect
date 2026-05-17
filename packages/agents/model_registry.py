"""Per-node model configuration, provider inference, and hackathon track mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from gemini_client import (
    GEMINI_EMBEDDING_MODEL,
    GEMINI_FLASH_MODEL,
    is_gemini_model_name,
)
from loguru import logger
from shared.models.agent import ModelAttributionEntry

TRACK_GOOGLE_GEMINI = "google_gemini"
TRACK_FEATHERLESS = "featherless"
TRACK_SPEECHMATICS = "speechmatics"
TRACK_VULTR = "vultr"

GEMINI_DEFAULT_FLASH = GEMINI_FLASH_MODEL
GEMINI_DEFAULT_EMBEDDING = GEMINI_EMBEDDING_MODEL
FEATHERLESS_DEFAULT_PRIVACY_MODEL = "Qwen/Qwen2.5-7B-Instruct"


@dataclass(frozen=True)
class NodeModelSpec:
    node_id: str
    env_var: str
    default_model: str
    default_backend: str
    hackathon_tracks: tuple[str, ...]


NODE_SPECS: dict[str, NodeModelSpec] = {
    "router": NodeModelSpec(
        node_id="router",
        env_var="ROUTER_MODEL",
        default_model=GEMINI_DEFAULT_FLASH,
        default_backend="google-genai",
        hackathon_tracks=(TRACK_GOOGLE_GEMINI,),
    ),
    "intelligence": NodeModelSpec(
        node_id="intelligence",
        env_var="INTELLIGENCE_MODEL",
        default_model=GEMINI_DEFAULT_FLASH,
        default_backend="google-genai",
        hackathon_tracks=(TRACK_GOOGLE_GEMINI,),
    ),
    "explainer": NodeModelSpec(
        node_id="explainer",
        env_var="EXPLAINER_MODEL",
        default_model=GEMINI_DEFAULT_FLASH,
        default_backend="google-genai",
        hackathon_tracks=(TRACK_GOOGLE_GEMINI,),
    ),
    "embeddings": NodeModelSpec(
        node_id="embeddings",
        env_var="EMBEDDING_MODEL",
        default_model=GEMINI_DEFAULT_EMBEDDING,
        default_backend="google-genai",
        hackathon_tracks=(TRACK_GOOGLE_GEMINI,),
    ),
    "privacy_guard": NodeModelSpec(
        node_id="privacy_guard",
        env_var="PRIVACY_GUARD_MODEL",
        default_model=FEATHERLESS_DEFAULT_PRIVACY_MODEL,
        default_backend="featherless",
        hackathon_tracks=(TRACK_FEATHERLESS,),
    ),
    "voice_input": NodeModelSpec(
        node_id="voice_input",
        env_var="SPEECHMATICS_MODEL",
        default_model="enhanced",
        default_backend="speechmatics",
        hackathon_tracks=(TRACK_SPEECHMATICS,),
    ),
}


def ensure_env_loaded() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    load_dotenv(repo_root / ".env", override=False)
    _apply_gemini_defaults()
    _apply_featherless_defaults()


def _apply_gemini_defaults() -> None:
    """Pin all non-privacy model defaults to Gemini."""
    if not os.getenv("ROUTER_MODEL", "").strip():
        os.environ["ROUTER_MODEL"] = GEMINI_DEFAULT_FLASH
    if not os.getenv("INTELLIGENCE_MODEL", "").strip():
        os.environ["INTELLIGENCE_MODEL"] = GEMINI_DEFAULT_FLASH
    if not os.getenv("EXPLAINER_MODEL", "").strip():
        os.environ["EXPLAINER_MODEL"] = GEMINI_DEFAULT_FLASH
    if not os.getenv("EMBEDDING_MODEL", "").strip():
        os.environ["EMBEDDING_MODEL"] = GEMINI_DEFAULT_EMBEDDING


def _apply_featherless_defaults() -> None:
    if not os.getenv("PRIVACY_GUARD_MODEL", "").strip():
        os.environ["PRIVACY_GUARD_MODEL"] = FEATHERLESS_DEFAULT_PRIVACY_MODEL
    if not os.getenv("PRIVACY_GUARD_BACKEND", "").strip():
        os.environ["PRIVACY_GUARD_BACKEND"] = "featherless"


def infer_provider(model: str | None) -> str:
    if not model:
        return "heuristic"
    if is_gemini_model_name(model):
        return "google"
    return "unknown"


def is_gemini_model(model: str | None) -> bool:
    return infer_provider(model) == "google"


def configured_model_for_node(node_id: str) -> str | None:
    spec = NODE_SPECS.get(node_id)
    if spec is None:
        return None
    ensure_env_loaded()
    value = os.getenv(spec.env_var, "").strip()
    model = value or spec.default_model or None
    if TRACK_GOOGLE_GEMINI in spec.hackathon_tracks and not is_gemini_model_name(model):
        logger.warning(
            "{} model={!r} is not Gemini; using {}",
            node_id,
            model,
            spec.default_model,
        )
        return spec.default_model
    return model


def _hackathon_tracks_for(
    node_id: str,
    *,
    model: str | None,
    backend: str,
    used_gemini: bool,
) -> list[str]:
    """Tracks satisfied by this run — only when the model/backend actually matches."""
    tracks: list[str] = []
    if used_gemini:
        tracks.append(TRACK_GOOGLE_GEMINI)
    spec = NODE_SPECS.get(node_id)
    if spec is None:
        return tracks
    if backend == "featherless":
        tracks.append(TRACK_FEATHERLESS)
    if spec.default_backend == "speechmatics" and backend == "speechmatics":
        tracks.append(TRACK_SPEECHMATICS)
    return tracks


def attribution_for_configured_node(node_id: str) -> ModelAttributionEntry:
    spec = NODE_SPECS[node_id]
    model = configured_model_for_node(node_id)
    provider = infer_provider(model) if model else spec.default_backend
    if provider == "unknown" and spec.default_backend == "featherless":
        provider = "featherless"
    used_gemini = is_gemini_model(model)
    return ModelAttributionEntry(
        node=node_id,
        provider=provider,
        model=model,
        backend=spec.default_backend,
        hackathon_tracks=_hackathon_tracks_for(
            node_id, model=model, backend=spec.default_backend, used_gemini=used_gemini
        ),
        used_gemini=used_gemini,
    )


def attribution_from_invocation(
    node_id: str,
    *,
    model: str | None,
    backend: str,
) -> ModelAttributionEntry:
    provider = infer_provider(model) if model else backend
    if backend == "featherless":
        provider = "featherless"
    if backend == "heuristic":
        provider = "heuristic"
    used_gemini = is_gemini_model(model)
    return ModelAttributionEntry(
        node=node_id,
        provider=provider,
        model=model,
        backend=backend,
        hackathon_tracks=_hackathon_tracks_for(
            node_id, model=model, backend=backend, used_gemini=used_gemini
        ),
        used_gemini=used_gemini,
    )


def log_attribution(entry: ModelAttributionEntry) -> None:
    tracks = ",".join(entry.hackathon_tracks) or "none"
    logger.info(
        "MODEL_ATTRIBUTION node={} provider={} model={} backend={} "
        "used_gemini={} hackathon_tracks=[{}]",
        entry.node,
        entry.provider,
        entry.model or "-",
        entry.backend,
        entry.used_gemini,
        tracks,
    )
    if entry.used_gemini:
        logger.info(
            "HACKATHON_TRACK google_gemini node={} model={}",
            entry.node,
            entry.model,
        )


def log_configured_node(node_id: str) -> ModelAttributionEntry:
    entry = attribution_for_configured_node(node_id)
    log_attribution(entry)
    return entry


def gemini_nodes_summary() -> dict[str, str]:
    """Human-readable map for README / demo scripts."""
    ensure_env_loaded()
    summary: dict[str, str] = {}
    for node_id, spec in NODE_SPECS.items():
        if TRACK_GOOGLE_GEMINI in spec.hackathon_tracks:
            summary[node_id] = configured_model_for_node(node_id) or spec.default_model
    return summary
