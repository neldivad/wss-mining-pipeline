"""mining.v1 — one row per site or tenement, as the registry served it.

Emits facts, not aggregates. Each capture is split across several partitions
(see docs/pagination.md), so any total computed inside a parser would be a
total of one partition, not of the state. Counting belongs in queries, where
the whole observed_at slice is in scope.

The two facts worth the archive:

  site  stage    Operating / Care and Maintenance / Proposed / Under
                 Development / Shut / Undeveloped. Overwritten in place, so
                 the date a mine went dark exists nowhere else.
  ten   holder   who holds live ground. Consolidation is invisible after the
                 fact for the same reason.

Both carry commodity and site type alongside, because a stage change is only
readable if you know what the site produces and whether it is a mine at all.

Static properties (titles, coordinates, tenement type, survey status) are
deliberately not emitted. They cannot change in a way worth a time series, and
the raw archive keeps every field anyway — a later parser version can recover
them without re-fetching.
"""

import hashlib
import json
import re

from wss import derive

PARSER_VERSION = "2"

# 40% of tenement holders are named individuals ("SURNAME, FORENAME"), not
# companies — 1,446 of 3,604 at first capture, holding 14% of tenements. WA
# publishes them because a tenement register is a public record; this archive
# does not need to be a plaintext mirror of them. Corporate holders are the
# analytical subject and are kept verbatim; individuals become a stable digest
# so their holdings can still be followed across captures without the name.
#
# This is pseudonymisation, not anonymisation: anyone with the live register
# can re-identify a digest. The point is that this repository does not restate
# the names itself.
_CORPORATE = re.compile(
    r"\b(PTY|LTD|LIMITED|NL|INC|CORP|CORPORATION|COMPANY|HOLDINGS|RESOURCES|"
    r"MINING|MINERALS|GROUP|TRUST|COUNCIL|SHIRE|COMMISSION|AUTHORITY|"
    r"DEPARTMENT|MINISTERIAL|WATER|ASSOCIATES|PARTNERS|VENTURES|EXPLORATION)\b"
)


def _holder(name):
    """Corporate names verbatim; natural persons as a stable digest."""
    if _CORPORATE.search(name.upper()):
        return name
    return "individual:" + hashlib.sha256(name.upper().encode()).hexdigest()[:12]
SCHEMA_ID = "mining.v1"

# extract_da / extract_date is the service's own "as of" stamp. Preferring it
# over the fetch time means a re-fetch of unchanged rows restates the same
# observed_at instead of inventing a new observation.
_DATE_FIELDS = ("extract_da", "extract_date")


def _observed_at(attrs):
    for field in _DATE_FIELDS:
        raw = attrs.get(field)
        if raw in (None, "", "None"):
            continue
        try:
            ms = int(float(raw))
        except (TypeError, ValueError):
            continue
        if ms <= 0:
            continue
        import datetime

        return datetime.datetime.fromtimestamp(ms / 1000, datetime.UTC).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
    return None


def _text(value):
    if value in (None, "", "None"):
        return None
    return str(value).strip() or None


def _features(payload):
    doc = json.loads(payload.decode("utf-8", "replace"))
    if "error" in doc:
        raise derive.DeriveError(f"service returned an error payload: {doc['error']}")
    return [f.get("attributes", {}) for f in doc.get("features", [])]


def parse(payload, ctx):
    for attrs in _features(payload):
        observed_at = _observed_at(attrs)

        if "site_code" in attrs:
            site = _text(attrs.get("site_code"))
            if not site:
                continue
            entity = f"site:wa:{site}"
            fields = (
                ("stage", attrs.get("site_stage"), ""),
                ("commodity", attrs.get("target_com"), ""),
                ("site_type", attrs.get("site_type_"), ""),
            )
        else:
            ten = _text(attrs.get("tenid"))
            if not ten:
                continue
            entity = f"tenement:wa:{ten}"
            fields = (
                ("holder", _holder(_text(attrs.get("holder1")) or ""), ""),
                ("area", attrs.get("legal_area"), _text(attrs.get("unit_of_me")) or ""),
            )

        for metric, raw, unit in fields:
            value = _text(raw)
            if value is None:
                continue
            if metric == "area":
                try:
                    value = float(value)
                except ValueError:
                    continue
            yield derive.Observation(
                entity_id=entity,
                metric=metric,
                value=value,
                unit=unit,
                observed_at=observed_at,
            )


derive.register(SCHEMA_ID, parse, PARSER_VERSION)
