"""Server-only HTTP adapter for Qloo Search and Insights APIs."""

from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import ValidationError

from ..models.qloo import PlaceCandidate, QlooContribution, QlooEntity


class QlooServiceError(RuntimeError):
    """A public-safe failure classification for an upstream Qloo call."""

    def __init__(self, code: str, message: str, *, retryable: bool) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = retryable


class QlooService:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout_seconds: float = 15.0,
        max_results: int = 20,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._max_results = max_results
        self._transport = transport

    async def search_entities(
        self,
        query: str,
        entity_type: str | None = None,
        *,
        take: int = 10,
    ) -> list[QlooEntity]:
        params: dict[str, str | int] = {
            "query": query.strip(),
            "take": self._bounded_take(take),
        }
        if entity_type:
            params["types"] = self._entity_urn(entity_type)

        payload = await self._get("/search", params)
        try:
            return [self._normalize_entity(raw) for raw in self._entities(payload)]
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise self._invalid_response() from exc

    async def recommend_places(
        self,
        *,
        destination: str,
        entity_ids: list[str],
        take: int = 20,
    ) -> list[PlaceCandidate]:
        params: dict[str, str | int] = {
            "filter.type": "urn:entity:place",
            "filter.location.query": destination.strip(),
            "signal.interests.entities": ",".join(entity_ids),
            "feature.explainability": "true",
            "take": self._bounded_take(take),
        }
        payload = await self._get("/v2/insights", params)
        try:
            return [self._normalize_place(raw) for raw in self._entities(payload)]
        except (KeyError, TypeError, ValidationError, ValueError) as exc:
            raise self._invalid_response() from exc

    async def _get(
        self, path: str, params: Mapping[str, str | int]
    ) -> dict[str, Any]:
        if not self._api_key:
            raise QlooServiceError(
                "QLOO_NOT_CONFIGURED",
                "Qloo is not configured on the server.",
                retryable=False,
            )

        headers = {"accept": "application/json", "x-api-key": self._api_key}
        for attempt in range(2):
            try:
                async with httpx.AsyncClient(
                    timeout=self._timeout_seconds,
                    transport=self._transport,
                ) as client:
                    response = await client.get(
                        f"{self._base_url}{path}", params=params, headers=headers
                    )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 0:
                    continue
                raise QlooServiceError(
                    "QLOO_UNAVAILABLE",
                    "Qloo is temporarily unavailable.",
                    retryable=True,
                ) from exc

            if response.status_code in {401, 403}:
                raise QlooServiceError(
                    "QLOO_AUTH_FAILED",
                    "Qloo authentication failed.",
                    retryable=False,
                )
            if response.status_code == 429:
                if attempt == 0:
                    continue
                raise QlooServiceError(
                    "QLOO_RATE_LIMITED",
                    "Qloo is temporarily rate limited.",
                    retryable=True,
                )
            if response.status_code >= 500:
                if attempt == 0:
                    continue
                raise QlooServiceError(
                    "QLOO_UNAVAILABLE",
                    "Qloo is temporarily unavailable.",
                    retryable=True,
                )
            if response.status_code >= 400:
                raise QlooServiceError(
                    "QLOO_REQUEST_REJECTED",
                    "Qloo rejected the request.",
                    retryable=False,
                )

            try:
                payload = response.json()
            except ValueError as exc:
                raise self._invalid_response() from exc
            if not isinstance(payload, dict):
                raise self._invalid_response()
            return payload

        raise AssertionError("Qloo retry loop exhausted unexpectedly")

    def _bounded_take(self, requested: int) -> int:
        return max(1, min(requested, self._max_results))

    @staticmethod
    def _entity_urn(entity_type: str) -> str:
        if entity_type.startswith("urn:entity:"):
            return entity_type
        return f"urn:entity:{entity_type.strip()}"

    @staticmethod
    def _entities(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
        results = payload.get("results")
        if not isinstance(results, Mapping):
            raise TypeError("results must be an object")
        entities = results.get("entities")
        if not isinstance(entities, list):
            raise TypeError("results.entities must be an array")
        if not all(isinstance(item, Mapping) for item in entities):
            raise TypeError("each entity must be an object")
        return entities

    @classmethod
    def _normalize_entity(cls, raw: Mapping[str, Any]) -> QlooEntity:
        properties = cls._mapping(raw.get("properties"))
        image = cls._mapping(properties.get("image"))
        return QlooEntity(
            id=cls._required_string(raw, "entity_id"),
            name=cls._required_string(raw, "name"),
            entity_type=cls._subtype(raw.get("subtype")),
            description=cls._optional_string(properties.get("description")),
            image_url=cls._optional_string(image.get("url")),
        )

    @classmethod
    def _normalize_place(cls, raw: Mapping[str, Any]) -> PlaceCandidate:
        properties = cls._mapping(raw.get("properties"))
        image = cls._mapping(properties.get("image"))
        geocode = cls._mapping(properties.get("geocode"))
        query = cls._mapping(raw.get("query"))
        explainability = cls._mapping(query.get("explainability"))
        contributions = cls._normalize_contributions(explainability)

        tags = []
        raw_tags = raw.get("tags", [])
        if isinstance(raw_tags, list):
            for tag in raw_tags:
                if isinstance(tag, Mapping) and tag.get("name"):
                    tags.append(str(tag["name"]))

        return PlaceCandidate(
            id=cls._required_string(raw, "entity_id"),
            name=cls._required_string(raw, "name"),
            address=cls._address(properties.get("address")),
            description=cls._optional_string(properties.get("description")),
            image_url=cls._optional_string(image.get("url")),
            latitude=cls._optional_float(
                geocode.get("latitude", geocode.get("lat"))
            ),
            longitude=cls._optional_float(
                geocode.get("longitude", geocode.get("lng"))
            ),
            affinity=cls._optional_float(query.get("affinity")),
            tags=tags,
            contributions=contributions,
        )

    @classmethod
    def _normalize_contributions(
        cls, explainability: Mapping[str, Any]
    ) -> list[QlooContribution]:
        records: list[tuple[str | None, Any]] = []
        signals = explainability.get("signals")
        if isinstance(signals, list):
            records.extend((None, signal) for signal in signals)

        entity_signals = explainability.get("signal.interests.entities")
        if isinstance(entity_signals, Mapping):
            records.extend(
                (str(entity_id), value)
                for entity_id, value in entity_signals.items()
            )
        elif isinstance(entity_signals, list):
            records.extend((None, signal) for signal in entity_signals)

        contributions: list[QlooContribution] = []
        seen: set[str] = set()
        for entity_id_hint, value in records:
            signal = value if isinstance(value, Mapping) else {}
            entity_id = entity_id_hint or cls._optional_string(
                signal.get("entity_id", signal.get("id"))
            )
            if not entity_id or entity_id in seen:
                continue
            raw_score = value if isinstance(value, (int, float)) else signal.get(
                "score", signal.get("weight", signal.get("affinity"))
            )
            contributions.append(
                QlooContribution(
                    entity_id=entity_id,
                    name=cls._optional_string(signal.get("name")),
                    score=cls._optional_float(raw_score),
                )
            )
            seen.add(entity_id)
        return contributions

    @staticmethod
    def _mapping(value: Any) -> Mapping[str, Any]:
        return value if isinstance(value, Mapping) else {}

    @staticmethod
    def _required_string(value: Mapping[str, Any], key: str) -> str:
        candidate = value.get(key)
        if not isinstance(candidate, str) or not candidate.strip():
            raise ValueError(f"missing {key}")
        return candidate.strip()

    @staticmethod
    def _optional_string(value: Any) -> str | None:
        return value.strip() if isinstance(value, str) and value.strip() else None

    @staticmethod
    def _optional_float(value: Any) -> float | None:
        if value is None:
            return None
        return float(value)

    @classmethod
    def _address(cls, value: Any) -> str | None:
        if isinstance(value, str):
            return cls._optional_string(value)
        if isinstance(value, Mapping):
            return cls._optional_string(value.get("formatted"))
        return None

    @staticmethod
    def _subtype(value: Any) -> str:
        if not isinstance(value, str) or not value:
            return "unknown"
        return value.removeprefix("urn:entity:")

    @staticmethod
    def _invalid_response() -> QlooServiceError:
        return QlooServiceError(
            "QLOO_INVALID_RESPONSE",
            "Qloo returned an invalid response.",
            retryable=False,
        )

