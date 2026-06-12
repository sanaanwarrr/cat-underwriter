from __future__ import annotations

from pathlib import Path
import re

from .schemas import GuidelineFlag, TreatySlip


class GuidelineStore:
    """Tiny local guideline retrieval layer.

    The MVP uses keyword retrieval by default so it runs anywhere. If ChromaDB is installed,
    you can replace this class with a vector collection without changing the pipeline interface.
    """

    def __init__(self, guideline_dir: str | Path):
        self.guideline_dir = Path(guideline_dir)
        self.chunks = self._load_chunks()

    def _load_chunks(self) -> list[str]:
        chunks: list[str] = []
        if not self.guideline_dir.exists():
            return chunks
        for path in sorted(self.guideline_dir.glob("**/*")):
            if path.suffix.lower() not in {".txt", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for raw in re.split(r"\n\s*\n", text):
                chunk = raw.strip()
                if chunk:
                    chunks.append(f"[{path.name}] {chunk}")
        return chunks

    def search(self, query: str, k: int = 5) -> list[str]:
        if not self.chunks:
            return []
        terms = [t.lower() for t in re.findall(r"[a-zA-Z]{3,}", query)]
        scored = []
        for chunk in self.chunks:
            lowered = chunk.lower()
            score = sum(1 for term in terms if term in lowered)
            if score:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:k]]


def evaluate_guidelines(treaty: TreatySlip, store: GuidelineStore | None = None) -> list[GuidelineFlag]:
    """Create underwriting referral flags using transparent rules."""
    flags: list[GuidelineFlag] = []
    territories = " ".join(treaty.territories).lower()
    perils = " ".join(treaty.covered_perils).lower()
    excluded = " ".join(treaty.excluded_perils).lower()

    if "florida" in territories and any(p in perils for p in ["hurricane", "windstorm"]):
        evidence = _first_guideline(store, "Florida hurricane windstorm referral coastal")
        flags.append(
            GuidelineFlag(
                flag_type="referral",
                severity="warning",
                message="Florida hurricane/windstorm exposure requires underwriter referral.",
                evidence=evidence,
            )
        )

    if treaty.attachment_point_usd < 10_000_000 and any(p in perils for p in ["hurricane", "wildfire", "earthquake"]):
        evidence = _first_guideline(store, "minimum attachment catastrophe treaty")
        flags.append(
            GuidelineFlag(
                flag_type="appetite",
                severity="warning",
                message="Attachment point is low for catastrophe exposure.",
                evidence=evidence,
            )
        )

    if "flood" in perils and "flood" in excluded:
        flags.append(
            GuidelineFlag(
                flag_type="wording",
                severity="critical",
                message="Flood appears both covered and excluded; wording conflict requires review.",
            )
        )

    if treaty.confidence_score < 0.70:
        flags.append(
            GuidelineFlag(
                flag_type="data_quality",
                severity="warning",
                message="Extraction confidence below threshold; request cleaner slip or manual review.",
            )
        )

    if treaty.limit_amount_usd >= 100_000_000:
        flags.append(
            GuidelineFlag(
                flag_type="accumulation",
                severity="warning",
                message="Large limit may create aggregation exposure and should be checked against current portfolio.",
            )
        )

    return flags


def _first_guideline(store: GuidelineStore | None, query: str) -> str | None:
    if store is None:
        return None
    results = store.search(query, k=1)
    return results[0] if results else None
