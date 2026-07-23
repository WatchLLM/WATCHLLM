"""Strict, typed, forward-extensible WebProof configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml

from .exceptions import ConfigError

_PROVER_MODES = frozenset({"reclaim", "tlsnotary"})


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(loader: yaml.Loader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise ConfigError("configuration keys must be scalar values") from exc
        if duplicate:
            raise ConfigError(f"duplicate configuration key: {key!r}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping
)


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or not all(isinstance(k, str) for k in value):
        raise ConfigError(f"{location} must be a mapping with string keys")
    return value


def _unknown(data: Mapping[str, Any], allowed: set[str], location: str) -> None:
    keys = sorted(set(data) - allowed)
    if keys:
        raise ConfigError(f"unknown {location} key(s): {', '.join(keys)}")


@dataclass(frozen=True, slots=True)
class AggregationConfig:
    enabled: bool = True
    algorithm: str = "sha256-local-merkle-v1"
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RouteConfig:
    hostname: str
    prover: str
    include_subdomains: bool = False
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class WebProofConfig:
    version: int = 1
    aggregation: AggregationConfig = field(default_factory=AggregationConfig)
    routes: tuple[RouteConfig, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "WebProofConfig":
        data = _mapping(raw, "configuration")
        _unknown(data, {"version", "aggregation", "routes", "metadata"}, "top-level")
        version = data.get("version", 1)
        if type(version) is not int or version != 1:
            raise ConfigError("version must be the integer 1")

        aggregation_raw = _mapping(data.get("aggregation", {}), "aggregation")
        _unknown(aggregation_raw, {"enabled", "algorithm", "metadata"}, "aggregation")
        enabled = aggregation_raw.get("enabled", True)
        algorithm = aggregation_raw.get("algorithm", "sha256-local-merkle-v1")
        if type(enabled) is not bool:
            raise ConfigError("aggregation.enabled must be a boolean")
        if algorithm != "sha256-local-merkle-v1":
            raise ConfigError("aggregation.algorithm must be 'sha256-local-merkle-v1'")
        aggregation = AggregationConfig(
            enabled=enabled,
            algorithm=algorithm,
            metadata=dict(_mapping(aggregation_raw.get("metadata", {}), "aggregation.metadata")),
        )

        routes_raw = data.get("routes", [])
        if not isinstance(routes_raw, list):
            raise ConfigError("routes must be a list")
        routes: list[RouteConfig] = []
        identities: set[tuple[str, bool]] = set()
        for index, item in enumerate(routes_raw):
            route_raw = _mapping(item, f"routes[{index}]")
            _unknown(route_raw, {"hostname", "prover", "include_subdomains", "metadata"}, f"routes[{index}]")
            hostname = normalize_hostname(route_raw.get("hostname"), f"routes[{index}].hostname")
            prover = route_raw.get("prover")
            if prover not in _PROVER_MODES:
                raise ConfigError(f"routes[{index}].prover must be one of: reclaim, tlsnotary")
            include = route_raw.get("include_subdomains", False)
            if type(include) is not bool:
                raise ConfigError(f"routes[{index}].include_subdomains must be a boolean")
            identity = (hostname, include)
            if identity in identities:
                raise ConfigError(f"duplicate route for hostname {hostname!r} with include_subdomains={include}")
            identities.add(identity)
            routes.append(RouteConfig(
                hostname=hostname,
                prover=prover,
                include_subdomains=include,
                metadata=dict(_mapping(route_raw.get("metadata", {}), f"routes[{index}].metadata")),
            ))

        return cls(
            version=version,
            aggregation=aggregation,
            routes=tuple(routes),
            metadata=dict(_mapping(data.get("metadata", {}), "metadata")),
        )


def normalize_hostname(value: Any, location: str = "hostname") -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{location} must be a non-empty hostname")
    hostname = value.strip().rstrip(".").lower()
    if "://" in hostname or any(c in hostname for c in "/?#@:"):
        raise ConfigError(f"{location} must contain only a hostname, not a URL or port")
    try:
        normalized = hostname.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise ConfigError(f"{location} is not a valid IDNA hostname") from exc
    labels = normalized.split(".")
    if any(not label or len(label) > 63 or label.startswith("-") or label.endswith("-") for label in labels):
        raise ConfigError(f"{location} is not a valid hostname")
    if any(not all(ch.isalnum() or ch == "-" for ch in label) for label in labels):
        raise ConfigError(f"{location} is not a valid hostname")
    return normalized


def load_config(source: str | Path | Mapping[str, Any] | WebProofConfig) -> WebProofConfig:
    """Load configuration from a YAML path, mapping, or typed config object."""
    if isinstance(source, WebProofConfig):
        return source
    if isinstance(source, Mapping):
        return WebProofConfig.from_mapping(source)
    path = Path(source)
    try:
        raw = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except OSError as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"invalid YAML in {path}: {exc}") from exc
    if raw is None:
        raw = {}
    return WebProofConfig.from_mapping(_mapping(raw, "configuration"))
