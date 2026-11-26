# -*- coding: utf-8 -*-
"""특허 조사 범위를 외부 요청 없이 결정하는 재현 가능한 플래너.

이 파일은 네트워크를 호출하거나 자격 증명을 읽지 않는다. 사용자가 승인할
STOP GATE 표와 실행 전 예상 범위를 만들기 위한 순수 표준 라이브러리 CLI다.
웹 자동화가 허용되지 않은 소스는 ``blocked-rights``로, 발견에만 쓸 수 있는
소스는 ``discovery-only``로 남겨 자동 수집 성공처럼 위장하지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Iterable

SCHEMA_VERSION = 1

PRESETS = ("quick", "standard", "fto", "prosecution", "custom")
JURISDICTIONS = ("KR", "US", "EP", "WO", "JP", "CN")

KIPRIS_MODULES = (
    "publications",
    "cited_references",
    "registration",
    "legal_status",
    "trials",
    "rejections",
)

EXPANSION_AXES = (
    "keyword",
    "classification",
    "backward_citation",
    "family",
    "assignee",
    "cited_by",
)

KIPRIS_SOURCE_BY_MODULE = {
    "publications": "kipris_publications",
    "cited_references": "kipris_cited_references",
    "registration": "kipris_registration",
    "legal_status": "kipris_legal_status",
    "trials": "kipris_trials",
    "rejections": "kipris_rejections",
}

MODULE_REQUEST_ESTIMATES = {
    "publications": 3,
    "cited_references": 5,
    "registration": 5,
    "legal_status": 5,
    "trials": 3,
    "rejections": 3,
}

SOURCE_REGISTRY = {
    "kipris_publications": {
        "label": "KIPRIS Plus 공개·등록공보 REST",
        "jurisdictions": ("KR",),
        "default_state": "automatic",
        "planned_requests": MODULE_REQUEST_ESTIMATES["publications"],
        "evidence_role": "official",
        "url": "https://plus.kipris.or.kr/",
    },
    "kipris_cited_references": {
        "label": "KIPRIS Plus 인용문헌 REST",
        "jurisdictions": ("KR",),
        "default_state": "automatic",
        "planned_requests": MODULE_REQUEST_ESTIMATES["cited_references"],
        "evidence_role": "official",
        "url": "https://plus.kipris.or.kr/",
    },
    "kipris_registration": {
        "label": "KIPRIS Plus 등록·권리·존속기간 REST",
        "jurisdictions": ("KR",),
        "default_state": "automatic",
        "planned_requests": MODULE_REQUEST_ESTIMATES["registration"],
        "evidence_role": "official",
        "url": "https://plus.kipris.or.kr/",
    },
    "kipris_legal_status": {
        "label": "KIPRIS Plus 법적 상태(ST.27) REST",
        "jurisdictions": ("KR",),
        "default_state": "automatic",
        "planned_requests": MODULE_REQUEST_ESTIMATES["legal_status"],
        "evidence_role": "official",
        "url": "https://plus.kipris.or.kr/",
    },
    "kipris_trials": {
        "label": "KIPRIS Plus 심판사항 REST",
        "jurisdictions": ("KR",),
        "default_state": "automatic",
        "planned_requests": MODULE_REQUEST_ESTIMATES["trials"],
        "evidence_role": "official",
        "url": "https://plus.kipris.or.kr/",
    },
    "kipris_rejections": {
        "label": "KIPRIS Plus 거절결정서 REST",
        "jurisdictions": ("KR",),
        "default_state": "automatic",
        "planned_requests": MODULE_REQUEST_ESTIMATES["rejections"],
        "evidence_role": "official",
        "url": "https://plus.kipris.or.kr/",
    },
    "kipris_claim_history": {
        "label": "KIPRIS Plus 청구항 변동 이력 파일",
        "jurisdictions": ("KR",),
        "default_state": "manual",
        "planned_requests": 0,
        "evidence_role": "official",
        "url": "https://www.data.go.kr/data/15053797/fileData.do",
    },
    "google_patents": {
        "label": "Google Patents",
        "jurisdictions": JURISDICTIONS,
        "default_state": "discovery-only",
        "planned_requests": 1,
        "evidence_role": "discovery",
        "url": "https://patents.google.com/",
    },
    "epo_ops": {
        "label": "EPO Open Patent Services (OPS)",
        "jurisdictions": ("EP", "WO"),
        "default_state": "manual",
        "planned_requests": 5,
        "evidence_role": "official",
        "url": "https://www.epo.org/en/searching-for-patents/data/web-services/ops",
    },
    "uspto_public_search": {
        "label": "USPTO Patent Public Search",
        "jurisdictions": ("US",),
        "default_state": "manual",
        "planned_requests": 0,
        "evidence_role": "official",
        "url": "https://ppubs.uspto.gov/pubwebapp/",
    },
    "wipo_patentscope": {
        "label": "WIPO PATENTSCOPE 웹",
        "jurisdictions": ("WO",),
        "default_state": "blocked-rights",
        "planned_requests": 0,
        "evidence_role": "official",
        "url": "https://patentscope.wipo.int/",
    },
    "espacenet_web": {
        "label": "Espacenet 웹",
        "jurisdictions": ("EP",),
        "default_state": "blocked-rights",
        "planned_requests": 0,
        "evidence_role": "official",
        "url": "https://worldwide.espacenet.com/",
    },
    "j_platpat": {
        "label": "J-PlatPat",
        "jurisdictions": ("JP",),
        "default_state": "manual",
        "planned_requests": 0,
        "evidence_role": "official",
        "url": "https://www.j-platpat.inpit.go.jp/",
    },
    "cnipa_search": {
        "label": "CNIPA 특허 검색",
        "jurisdictions": ("CN",),
        "default_state": "manual",
        "planned_requests": 0,
        "evidence_role": "official",
        "url": "https://pss-system.cponline.cnipa.gov.cn/",
    },
}

EXTERNAL_SOURCE_IDS = tuple(
    source_id
    for source_id in SOURCE_REGISTRY
    if source_id not in set(KIPRIS_SOURCE_BY_MODULE.values())
)

PRESET_MODULES = {
    "quick": ("publications",),
    "standard": ("publications", "cited_references"),
    "fto": ("publications", "cited_references", "registration", "legal_status"),
    "prosecution": KIPRIS_MODULES,
    "custom": (),
}

PRESET_EXTERNAL_SOURCES = {
    "quick": (),
    "standard": ("google_patents",),
    "fto": ("google_patents",),
    "prosecution": ("kipris_claim_history", "google_patents"),
    "custom": (),
}

PRESET_AXES = {
    "quick": ("keyword", "classification"),
    "standard": (
        "keyword",
        "classification",
        "backward_citation",
        "family",
        "assignee",
    ),
    "fto": (
        "keyword",
        "classification",
        "backward_citation",
        "family",
        "assignee",
    ),
    "prosecution": (
        "keyword",
        "classification",
        "backward_citation",
        "family",
        "assignee",
    ),
    "custom": (),
}

JURISDICTION_OFFICIAL_SOURCES = {
    "KR": (),
    "US": ("uspto_public_search",),
    "EP": ("epo_ops", "espacenet_web"),
    "WO": ("epo_ops", "wipo_patentscope"),
    "JP": ("j_platpat",),
    "CN": ("cnipa_search",),
}

AXIS_REGISTRY = {
    "keyword": ("automatic", "키워드·정확 구문 축"),
    "classification": ("automatic", "IPC/CPC 정의 확인 후 분류 축"),
    "backward_citation": ("automatic", "공식 응답의 후방 인용 축"),
    "family": ("automatic", "공식 응답의 패밀리 1-hop 축"),
    "assignee": ("automatic", "출원인 축"),
    "cited_by": (
        "blocked-rights",
        "공식 KIPRIS 오퍼레이션이 확인되지 않아 자동화하지 않음",
    ),
}


class ScopePlanError(ValueError):
    """사용자 범위 입력이 계약을 위반했다."""


def _ordered_unique(values: Iterable[str], universe: tuple[str, ...]) -> tuple[str, ...]:
    requested = set(values)
    unknown = sorted(requested.difference(universe))
    if unknown:
        raise ScopePlanError("알 수 없는 값: " + ", ".join(unknown))
    return tuple(item for item in universe if item in requested)


def _jurisdiction_sources(
    jurisdictions: tuple[str, ...], preset: str
) -> tuple[str, ...]:
    if preset == "custom":
        return ()
    selected = []
    for jurisdiction in jurisdictions:
        selected.extend(JURISDICTION_OFFICIAL_SOURCES[jurisdiction])
    return _ordered_unique(selected, tuple(SOURCE_REGISTRY))


def _source_state(
    source_id: str,
    selected_ids: set[str],
    jurisdictions: tuple[str, ...],
    kipris_registered: bool,
    epo_ops_registered: bool,
) -> dict:
    spec = SOURCE_REGISTRY[source_id]
    applicable = bool(set(spec["jurisdictions"]).intersection(jurisdictions))
    if not applicable:
        selection_status = "not-applicable"
    elif source_id in selected_ids:
        selection_status = "selected"
    else:
        selection_status = "omitted-by-user"

    state = spec["default_state"]
    reason = ""
    if source_id.startswith("kipris_") and state == "automatic":
        if kipris_registered:
            reason = "등록된 KIPRIS Plus REST 상품과 키로 자동 실행 가능"
        else:
            state = "manual"
            reason = "KIPRIS Plus 상품·키 준비 여부가 확인되지 않아 자동 실행 보류"
    elif source_id == "epo_ops":
        if epo_ops_registered:
            state = "automatic"
            reason = "등록된 EPO OPS 자격 증명으로 API 실행 가능"
        else:
            state = "manual"
            reason = "EPO OPS 등록·자격 증명이 확인되지 않아 수동 확인으로 계획"
    elif state == "discovery-only":
        reason = "후보 발견 전용이며 판정 근거로 사용하기 전 공식 원문 재검증 필요"
    elif state == "blocked-rights":
        reason = "웹 자동 질의를 실행하지 않으며 사용자가 공식 웹에서 직접 확인"
    elif state == "manual":
        reason = "공식 웹 또는 파일을 사용자가 직접 확인"

    automated_requests = (
        int(spec["planned_requests"])
        if selection_status == "selected" and state == "automatic"
        else 0
    )
    planned_requests = (
        int(spec["planned_requests"]) if selection_status == "selected" else 0
    )
    return {
        "id": source_id,
        "label": spec["label"],
        "selection_status": selection_status,
        "execution_state": state,
        "evidence_role": spec["evidence_role"],
        "jurisdictions": list(spec["jurisdictions"]),
        "planned_requests": planned_requests,
        "automated_requests": automated_requests,
        "reason": reason,
        "url": spec["url"],
    }


def _axis_state(axis: str, selected_axes: set[str]) -> dict:
    state, reason = AXIS_REGISTRY[axis]
    return {
        "id": axis,
        "selection_status": "selected" if axis in selected_axes else "omitted-by-user",
        "execution_state": state,
        "reason": reason,
    }


def resolve_scope(
    *,
    preset: str = "standard",
    jurisdictions: Iterable[str] = ("KR",),
    kipris_modules: Iterable[str] | None = None,
    external_sources: Iterable[str] | None = None,
    expansion_axes: Iterable[str] | None = None,
    kipris_registered: bool = False,
    epo_ops_registered: bool = False,
) -> dict:
    """요청 범위를 정규화하고 모든 포함·제외 상태가 보이는 계획을 반환한다."""
    if preset not in PRESETS:
        raise ScopePlanError(f"알 수 없는 preset: {preset}")
    jurisdictions_resolved = _ordered_unique(jurisdictions, JURISDICTIONS)
    if not jurisdictions_resolved:
        raise ScopePlanError("jurisdiction은 최소 1개 필요")

    module_input = PRESET_MODULES[preset] if kipris_modules is None else kipris_modules
    modules = _ordered_unique(module_input, KIPRIS_MODULES)
    if "KR" not in jurisdictions_resolved:
        if kipris_modules is not None and modules:
            raise ScopePlanError(
                "KIPRIS REST 모듈은 KR 관할을 함께 선택한 경우에만 지정할 수 있음"
            )
        # preset의 KIPRIS 기본값은 KR 관할에서만 적용한다. EP/US 조사에 한국
        # 모듈 호출량이 포함되는 것처럼 보이지 않도록 계획 단계에서 제거한다.
        modules = ()
    source_input = (
        PRESET_EXTERNAL_SOURCES[preset]
        if external_sources is None
        else external_sources
    )
    sources = _ordered_unique(source_input, EXTERNAL_SOURCE_IDS)
    axis_input = PRESET_AXES[preset] if expansion_axes is None else expansion_axes
    axes = _ordered_unique(axis_input, EXPANSION_AXES)

    if preset == "custom" and not (modules or sources or axes):
        raise ScopePlanError(
            "custom은 --kipris-module, --source, --axis 중 하나 이상을 선택해야 함"
        )

    selected_source_ids = set(KIPRIS_SOURCE_BY_MODULE[module] for module in modules)
    selected_source_ids.update(sources)
    selected_source_ids.update(_jurisdiction_sources(jurisdictions_resolved, preset))

    source_states = [
        _source_state(
            source_id,
            selected_source_ids,
            jurisdictions_resolved,
            kipris_registered,
            epo_ops_registered,
        )
        for source_id in SOURCE_REGISTRY
    ]
    axis_states = [_axis_state(axis, set(axes)) for axis in EXPANSION_AXES]

    selected_states = [
        state for state in source_states if state["selection_status"] == "selected"
    ]
    evidence_jurisdictions = {
        jurisdiction: any(
            state["selection_status"] == "selected"
            and state["evidence_role"] == "official"
            and jurisdiction in state["jurisdictions"]
            for state in source_states
        )
        for jurisdiction in jurisdictions_resolved
    }
    coverage_gaps = [
        f"{jurisdiction}: 공식 판정 근거 소스 미선택"
        for jurisdiction, covered in evidence_jurisdictions.items()
        if not covered
    ]
    if "cited_by" in axes:
        coverage_gaps.append("cited_by: 허용된 공식 자동 오퍼레이션 미확인")

    canonical = {
        "schema_version": SCHEMA_VERSION,
        "preset": preset,
        "jurisdictions": list(jurisdictions_resolved),
        "kipris_rest_modules": list(modules),
        "external_sources": sorted(
            source_id
            for source_id in selected_source_ids
            if source_id not in KIPRIS_SOURCE_BY_MODULE.values()
        ),
        "expansion_axes": list(axes),
        "kipris_registered": bool(kipris_registered),
        "epo_ops_registered": bool(epo_ops_registered),
    }
    fingerprint = hashlib.sha256(
        json.dumps(
            canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()

    planned_requests = sum(state["planned_requests"] for state in selected_states)
    automated_requests = sum(state["automated_requests"] for state in selected_states)
    requires_manual = any(
        state["execution_state"] in {"manual", "blocked-rights"}
        for state in selected_states
    )
    discovery_selected = any(
        state["execution_state"] == "discovery-only" for state in selected_states
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "preset": preset,
        "jurisdictions": list(jurisdictions_resolved),
        "kipris_rest_modules": list(modules),
        "selected_expansion_axes": list(axes),
        "sources": source_states,
        "expansion_axes": axis_states,
        "estimates": {
            "planned_external_requests": planned_requests,
            "automated_external_requests": automated_requests,
            "model_tokens": 0,
        },
        "coverage": {
            "claim": "scope-plan-only",
            "requires_manual_verification": requires_manual,
            "discovery_sources_require_official_reverification": discovery_selected,
            "gaps": coverage_gaps,
        },
        "scope_fingerprint_sha256": fingerprint,
        "canonical_request": canonical,
        "safety": {
            "network_called": False,
            "wipo_patentscope_web_automated": False,
            "espacenet_web_automated": False,
            "secrets_read_or_emitted": False,
        },
    }


def _csv_values(values: list[str] | None) -> list[str] | None:
    if values is None:
        return None
    flattened = []
    for value in values:
        flattened.extend(part.strip() for part in value.split(",") if part.strip())
    return flattened


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="외부 호출 없이 특허 조사 범위·권리 상태·예상 요청량을 계획합니다."
    )
    parser.add_argument("--preset", choices=PRESETS, default="standard")
    parser.add_argument(
        "--jurisdiction",
        action="append",
        choices=JURISDICTIONS,
        help="반복 지정 가능(기본 KR)",
    )
    parser.add_argument(
        "--kipris-module",
        action="append",
        choices=KIPRIS_MODULES,
        help="지정하면 preset의 KIPRIS REST 모듈을 대체",
    )
    parser.add_argument(
        "--source",
        action="append",
        choices=EXTERNAL_SOURCE_IDS,
        help="지정하면 preset의 외부 소스를 대체",
    )
    parser.add_argument(
        "--axis",
        action="append",
        choices=EXPANSION_AXES,
        help="지정하면 preset의 확장 축을 대체",
    )
    parser.add_argument(
        "--kipris-registered",
        action="store_true",
        help="KIPRIS Plus 상품·키 준비를 확인한 경우에만 사용(키 값은 받지 않음)",
    )
    parser.add_argument(
        "--epo-ops-registered",
        action="store_true",
        help="EPO OPS 등록·자격 증명 준비를 확인한 경우에만 사용",
    )
    parser.add_argument("--out", help="새 JSON 파일로 저장(기존 파일 덮어쓰기 거부)")
    parser.add_argument("--compact", action="store_true", help="한 줄 JSON 출력")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        plan = resolve_scope(
            preset=args.preset,
            jurisdictions=args.jurisdiction or ("KR",),
            kipris_modules=_csv_values(args.kipris_module),
            external_sources=_csv_values(args.source),
            expansion_axes=_csv_values(args.axis),
            kipris_registered=args.kipris_registered,
            epo_ops_registered=args.epo_ops_registered,
        )
    except ScopePlanError as exc:
        parser.error(str(exc))

    rendered = json.dumps(
        plan,
        ensure_ascii=False,
        sort_keys=True,
        indent=None if args.compact else 2,
    )
    if args.out:
        path = os.path.abspath(args.out)
        try:
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(rendered + "\n")
        except FileExistsError:
            parser.error("기존 --out 파일 덮어쓰기 거부")
    else:
        sys.stdout.write(rendered + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
