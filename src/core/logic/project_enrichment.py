import glob
import json
import os
import re
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

from eo_lib import InitiativeController
from loguru import logger
from sqlalchemy import text

from src.core.logic.initiative_identity import normalize_text
from src.tracking.recorder import tracking_recorder

RESEARCH_PROJECT_TYPE = "Research Project"
FUZZY_THRESHOLD = 0.90


def normalize_project_code(value: Any) -> str:
    """Extracts the numeric SigPesq project code from a value like 'PJ 6020'."""
    if value is None:
        return ""
    match = re.search(r"\d+", str(value))
    return match.group(0) if match else ""


class ProjectEnrichmentLoader:
    """
    Enriches Research Project initiatives ALREADY in the database with content
    extracted from SigPesq project document files (``PJ_*.json``).

    Scope
    -----
    * Only initiatives that already exist as Research Projects in the DB.
      A PJ file is matched to an initiative by, in order of confidence:
        1. ``sigpesq_project_code``  — the code recorded in the tracking tables
           when the SigPesq Excel report was ingested. These initiatives are all
           APPROVED (``ParecerDiretoria == "Aprovado"``); the Excel loader only
           persists approved projects.
        2. ``title_exact``           — normalized title equals a Research Project
           initiative name (unique match).
        3. ``title_fuzzy``           — best normalized-title similarity ≥ 0.90.
           Flagged ``needs_review`` because a fuzzy match can be a false positive.
      PJ files matching nothing (truly new projects) are skipped.

    What is written
    ---------------
    * ``description`` (initiatives column): filled only when currently empty,
      unless ``overwrite=True``. Excel ``Resumo`` stays authoritative otherwise.
    * ``enrichment_json`` (new initiatives column): the richer document fields
      that have no dedicated column — objectives, dated schedule, research line,
      structured keywords, knowledge area — plus provenance and the match
      strategy / ``needs_review`` flag. Always (re)written for a matched project,
      since this loader fully owns that column.
    """

    SOURCE_SYSTEM = "sigpesq_project_files"

    def __init__(self, overwrite: bool = False, dry_run: bool = False):
        self.controller = InitiativeController()
        self.overwrite = overwrite
        self.dry_run = dry_run

    @property
    def _session(self):
        return self.controller._service._repository._session

    # ------------------------------------------------------------------ schema
    def ensure_schema(self) -> None:
        """Adds the ``enrichment_json`` column to ``initiatives`` if missing."""
        cols = {
            row[1]
            for row in self._session.execute(text("PRAGMA table_info(initiatives)")).fetchall()
        }
        if "enrichment_json" not in cols:
            logger.info("Adding column initiatives.enrichment_json (TEXT)")
            self._session.execute(text("ALTER TABLE initiatives ADD COLUMN enrichment_json TEXT"))
            self._session.commit()

    # ------------------------------------------------------------------ indexes
    def _load_code_index(self) -> Dict[str, int]:
        """``project_code -> initiative_id`` for APPROVED SigPesq projects, using
        the tracking tables as the authoritative code<->initiative link."""
        rows = self._session.execute(
            text(
                """
                SELECT sr.raw_payload_json AS payload,
                       aa.canonical_entity_id AS init_id
                FROM source_records sr
                JOIN attribute_assertions aa
                  ON aa.source_record_id = sr.id
                 AND aa.canonical_entity_type = 'initiative'
                WHERE sr.source_system = 'sigpesq_research_projects'
                  AND sr.source_entity_type = 'initiative'
                """
            )
        ).fetchall()

        index: Dict[str, int] = {}
        for payload, init_id in rows:
            try:
                data = json.loads(payload) if isinstance(payload, str) else payload
            except (TypeError, json.JSONDecodeError):
                continue
            if not isinstance(data, dict):
                continue
            if "aprovado" not in str(data.get("ParecerDiretoria") or "").lower():
                continue
            code = normalize_project_code(data.get("Id"))
            if code and init_id and code not in index:
                index[code] = init_id
        return index

    def _load_research_project_names(self) -> Tuple[Dict[str, List[int]], List[Tuple[int, str]]]:
        """Returns (normalized_name -> [initiative_id], [(id, normalized_name)]) for
        Research Project initiatives only (advisorships excluded)."""
        rows = self._session.execute(
            text(
                """
                SELECT i.id, i.name
                FROM initiatives i
                JOIN initiative_types t ON i.initiative_type_id = t.id
                WHERE t.name = :type_name
                """
            ),
            {"type_name": RESEARCH_PROJECT_TYPE},
        ).fetchall()

        by_name: Dict[str, List[int]] = {}
        norm_list: List[Tuple[int, str]] = []
        for init_id, name in rows:
            norm = normalize_text(name)
            if not norm:
                continue
            by_name.setdefault(norm, []).append(init_id)
            norm_list.append((init_id, norm))
        return by_name, norm_list

    def _load_current_descriptions(self) -> Dict[int, str]:
        rows = self._session.execute(text("SELECT id, description FROM initiatives")).fetchall()
        return {row[0]: (row[1] or "") for row in rows}

    # ------------------------------------------------------------------ matching
    def _match(
        self,
        pj: Dict[str, Any],
        code_index: Dict[str, int],
        name_index: Dict[str, List[int]],
        norm_names: List[Tuple[int, str]],
    ) -> Optional[Tuple[int, str, bool]]:
        """Returns (initiative_id, match_strategy, needs_review) or None."""
        code = normalize_project_code(pj.get("codigo"))
        if code and code in code_index:
            return code_index[code], "sigpesq_project_code", False

        title = pj.get("titulo")
        norm_title = normalize_text(title) if title else ""
        if not norm_title:
            return None

        exact = name_index.get(norm_title)
        if exact:
            # Unique exact match is trusted; ambiguous one is flagged for review.
            return exact[0], "title_exact", len(exact) > 1

        best_id, best_ratio = None, 0.0
        for init_id, cand in norm_names:
            ratio = SequenceMatcher(None, norm_title, cand).ratio()
            if ratio > best_ratio:
                best_id, best_ratio = init_id, ratio
        if best_id is not None and best_ratio >= FUZZY_THRESHOLD:
            return best_id, "title_fuzzy", True
        return None

    # ------------------------------------------------------------------ payload
    @staticmethod
    def _compose_description(pj: Dict[str, Any]) -> Optional[str]:
        """Prefers the free-text ``descricao``; falls back to the general objective."""
        desc = (pj.get("descricao") or "").strip()
        if desc:
            return desc
        geral = ((pj.get("objetivos") or {}).get("geral") or "").strip()
        return geral or None

    @staticmethod
    def _build_enrichment(
        pj: Dict[str, Any], *, code: str, strategy: str, needs_review: bool
    ) -> Dict[str, Any]:
        meta = pj.get("_meta") or {}
        return {
            "source": ProjectEnrichmentLoader.SOURCE_SYSTEM,
            "project_code": code or None,
            "match_strategy": strategy,
            "needs_review": needs_review,
            "objetivos": pj.get("objetivos") or {},
            "cronograma": pj.get("cronograma") or [],
            "linha_pesquisa": pj.get("linha_pesquisa"),
            "palavras_chave": pj.get("palavras_chave") or [],
            "area_conhecimento": pj.get("area_conhecimento"),
            "extracted_at": meta.get("extraido_em"),
            "extraction_model": meta.get("modelo"),
            "source_file": meta.get("arquivo"),
        }

    # ------------------------------------------------------------------ main
    def load(self, pj_dir: str) -> Dict[str, int]:
        self.ensure_schema()

        code_index = self._load_code_index()
        name_index, norm_names = self._load_research_project_names()
        descriptions = self._load_current_descriptions()
        logger.info(
            f"Indexes ready: {len(code_index)} approved-by-code, "
            f"{len(norm_names)} research-project names"
        )

        files = sorted(glob.glob(os.path.join(pj_dir, "PJ_*.json")))
        logger.info(f"Found {len(files)} PJ document files in {pj_dir}")

        stats = {
            "enriched": 0,
            "desc_filled": 0,
            "desc_kept_existing": 0,
            "needs_review": 0,
            "by_code": 0,
            "by_title_exact": 0,
            "by_title_fuzzy": 0,
            "skipped_no_match": 0,
            "skipped_collision": 0,
        }

        # First pass: match every file. Then resolve so each initiative is
        # enriched at most once, highest-confidence match winning
        # (code > title_exact > title_fuzzy). This prevents a low-confidence
        # title match from overwriting a code match on the same initiative.
        priority = {"sigpesq_project_code": 0, "title_exact": 1, "title_fuzzy": 2}
        candidates = []
        for path in files:
            try:
                with open(path, encoding="utf-8") as fh:
                    pj = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(f"Could not read {path}: {exc}")
                continue
            match = self._match(pj, code_index, name_index, norm_names)
            if not match:
                stats["skipped_no_match"] += 1
                continue
            init_id, strategy, needs_review = match
            candidates.append((priority[strategy], path, pj, init_id, strategy, needs_review))

        candidates.sort(key=lambda c: (c[0], c[1]))
        claimed: set[int] = set()

        for _prio, path, pj, init_id, strategy, needs_review in candidates:
            if init_id in claimed:
                stats["skipped_collision"] += 1
                logger.debug(f"init {init_id} already claimed; skipping {os.path.basename(path)}")
                continue
            claimed.add(init_id)

            code = normalize_project_code(pj.get("codigo"))
            enrichment = self._build_enrichment(
                pj, code=code, strategy=strategy, needs_review=needs_review
            )

            # description policy: fill only when empty (unless overwrite)
            new_desc = self._compose_description(pj)
            current = descriptions.get(init_id, "").strip()
            write_desc = bool(new_desc) and (self.overwrite or not current)

            if self.dry_run:
                action = "fill" if (write_desc and not current) else (
                    "overwrite" if write_desc else "keep"
                )
                logger.info(
                    f"[dry-run][{strategy}] init {init_id} desc={action} "
                    f"review={needs_review} (code={code or '-'})"
                )
            else:
                self._apply(init_id, enrichment, new_desc if write_desc else None)
                self._record_tracking(
                    init_id=init_id,
                    code=code,
                    strategy=strategy,
                    enrichment=enrichment,
                    desc_written=new_desc if write_desc else None,
                    path=path,
                    pj=pj,
                )

            stats["enriched"] += 1
            stats["by_" + {"sigpesq_project_code": "code", "title_exact": "title_exact", "title_fuzzy": "title_fuzzy"}[strategy]] += 1
            if needs_review:
                stats["needs_review"] += 1
            if write_desc and not current:
                stats["desc_filled"] += 1
            elif current and not self.overwrite:
                stats["desc_kept_existing"] += 1

        logger.info(f"Enrichment complete ({'dry-run' if self.dry_run else 'applied'}): {stats}")
        return stats

    def _apply(self, init_id: int, enrichment: Dict[str, Any], description: Optional[str]) -> None:
        payload = json.dumps(enrichment, ensure_ascii=False)
        if description:
            self._session.execute(
                text("UPDATE initiatives SET description = :d, enrichment_json = :j WHERE id = :id"),
                {"d": description, "j": payload, "id": init_id},
            )
        else:
            self._session.execute(
                text("UPDATE initiatives SET enrichment_json = :j WHERE id = :id"),
                {"j": payload, "id": init_id},
            )
        self._session.commit()

    def _record_tracking(
        self,
        *,
        init_id: int,
        code: str,
        strategy: str,
        enrichment: Dict[str, Any],
        desc_written: Optional[str],
        path: str,
        pj: Dict[str, Any],
    ) -> None:
        if not tracking_recorder.has_active_run():
            return
        source_record = tracking_recorder.record_source_record(
            source_entity_type="initiative",
            payload=pj,
            source_record_id=f"PJ {code}" if code else os.path.basename(path),
            source_file=os.path.basename(path),
            source_path=path,
        )
        sr_id = getattr(source_record, "id", None)
        tracking_recorder.record_entity_match(
            source_record_id=sr_id,
            canonical_entity_type="initiative",
            canonical_entity_id=init_id,
            match_strategy=strategy,
            match_confidence=1.0 if strategy != "title_fuzzy" else 0.9,
        )
        selected = {"enrichment": enrichment}
        if desc_written:
            selected["description"] = desc_written
        tracking_recorder.record_attribute_assertions(
            source_record_id=sr_id,
            canonical_entity_type="initiative",
            canonical_entity_id=init_id,
            selected_attributes=selected,
            selection_reason="sigpesq_project_file_enrichment",
        )
        tracking_recorder.record_change(
            source_record_id=sr_id,
            canonical_entity_type="initiative",
            canonical_entity_id=init_id,
            operation="update",
            changed_fields=list(selected.keys()),
            after={"initiative_id": init_id, **selected},
            reason="ProjectEnrichmentLoader applied",
        )

    # ------------------------------------------------------- ingest new
    @staticmethod
    def _parse_sql_datetime(value: Any) -> Optional[str]:
        """Turns a 'YYYY-MM-DD' string into the datetime format the ORM stores."""
        if not value:
            return None
        match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(value))
        if not match:
            return None
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)} 00:00:00.000000"

    @staticmethod
    def _derive_status(start: Optional[str], end: Optional[str]) -> str:
        """Best-effort status for a documented project without a diretoria parecer."""
        from datetime import datetime

        if end:
            match = re.match(r"^(\d{4})-(\d{2})-(\d{2})", str(end))
            if match:
                end_dt = datetime(int(match.group(1)), int(match.group(2)), int(match.group(3)))
                return "Concluded" if end_dt < datetime.now() else "Active"
        return "Active" if start else "Unknown"

    def _lookup_org_and_type(self) -> Tuple[Optional[int], int]:
        type_row = self._session.execute(
            text("SELECT id FROM initiative_types WHERE name = :n LIMIT 1"),
            {"n": RESEARCH_PROJECT_TYPE},
        ).fetchone()
        type_id = type_row[0] if type_row else 1
        org_row = self._session.execute(
            text(
                """
                SELECT organization_id FROM initiatives
                WHERE organization_id IS NOT NULL
                GROUP BY organization_id ORDER BY COUNT(*) DESC LIMIT 1
                """
            )
        ).fetchone()
        return (org_row[0] if org_row else None), type_id

    def ingest_unmatched(self, pj_dir: str) -> Dict[str, int]:
        """
        Creates NEW Research Project initiatives from PJ document files that match
        no existing initiative. Only content-rich files are ingested (title +
        description + general objective or schedule); titles are deduplicated and
        anything whose name already exists is skipped. Every created initiative is
        flagged ``needs_review`` inside its enrichment payload.
        """
        self.ensure_schema()
        code_index = self._load_code_index()
        name_index, norm_names = self._load_research_project_names()
        existing_names = set(name_index.keys())
        org_id, type_id = self._lookup_org_and_type()

        files = sorted(glob.glob(os.path.join(pj_dir, "PJ_*.json")))
        stats = {"created": 0, "skipped_matched": 0, "skipped_poor": 0, "skipped_duplicate": 0}
        seen_titles: set[str] = set()

        for path in files:
            try:
                with open(path, encoding="utf-8") as fh:
                    pj = json.load(fh)
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning(f"Could not read {path}: {exc}")
                continue

            if self._match(pj, code_index, name_index, norm_names) is not None:
                stats["skipped_matched"] += 1
                continue

            title = (pj.get("titulo") or "").strip()
            descricao = (pj.get("descricao") or "").strip()
            geral = ((pj.get("objetivos") or {}).get("geral") or "").strip()
            cronograma = pj.get("cronograma") or []
            # Content bar: needs a title, a description, and either objectives or a schedule.
            if not title or not descricao or not (geral or cronograma):
                stats["skipped_poor"] += 1
                continue

            norm = normalize_text(title)
            if norm in existing_names or norm in seen_titles:
                stats["skipped_duplicate"] += 1
                continue
            seen_titles.add(norm)

            code = normalize_project_code(pj.get("codigo"))
            enrichment = self._build_enrichment(
                pj, code=code, strategy="new_from_document", needs_review=True
            )
            datas = pj.get("datas") or {}
            start_sql = self._parse_sql_datetime(datas.get("inicio"))
            end_sql = self._parse_sql_datetime(datas.get("fim"))
            status = self._derive_status(datas.get("inicio"), datas.get("fim"))
            description = descricao or geral

            if self.dry_run:
                logger.info(f"[dry-run][new] would create '{title[:60]}' (code={code or '-'}, {status})")
                stats["created"] += 1
                continue

            result = self._session.execute(
                text(
                    """
                    INSERT INTO initiatives
                        (name, status, description, start_date, end_date,
                         initiative_type_id, organization_id, parent_id, enrichment_json)
                    VALUES (:name, :status, :desc, :start, :end, :type_id, :org_id, NULL, :j)
                    """
                ),
                {
                    "name": title,
                    "status": status,
                    "desc": description,
                    "start": start_sql,
                    "end": end_sql,
                    "type_id": type_id,
                    "org_id": org_id,
                    "j": json.dumps(enrichment, ensure_ascii=False),
                },
            )
            self._session.commit()
            new_id = result.lastrowid
            self._record_tracking(
                init_id=new_id,
                code=code,
                strategy="new_from_document",
                enrichment=enrichment,
                desc_written=description,
                path=path,
                pj=pj,
            )
            existing_names.add(norm)
            stats["created"] += 1
            logger.info(f"[new] initiative {new_id} created: {title[:60]} ({status})")

        logger.info(f"Ingest unmatched complete ({'dry-run' if self.dry_run else 'applied'}): {stats}")
        return stats
