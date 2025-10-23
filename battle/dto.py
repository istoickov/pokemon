from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class PokeAPIPokemonDTO:
    id: int
    name: str
    base_experience: Optional[int]
    height: Optional[int]
    weight: Optional[int]
    stats: Dict[str, int]
    stat_urls: Dict[str, str]  # URLs to stat details with affecting_moves
    types: List[str]
    abilities: List[str]

    @staticmethod
    def from_api_json(data: Dict[str, Any]) -> "PokeAPIPokemonDTO":
        stats = {s["stat"]["name"]: s["base_stat"] for s in data.get("stats", [])}
        stat_urls = {s["stat"]["name"]: s["stat"]["url"] for s in data.get("stats", [])}
        types = [t["type"]["name"] for t in data.get("types", [])]
        abilities = [a["ability"]["name"] for a in data.get("abilities", [])]
        return PokeAPIPokemonDTO(
            id=data["id"],
            name=data["name"],
            base_experience=data.get("base_experience"),
            height=data.get("height"),
            weight=data.get("weight"),
            stats=stats,
            stat_urls=stat_urls,
            types=types,
            abilities=abilities,
        )


@dataclass
class BattleResultDTO:
    winner_name: Optional[str]
    metrics: Dict[str, Any]
    algorithm_version: str


@dataclass
class BattleCreateResponseDTO:
    id: int
    attacker: str
    defender: str
    winner: Optional[str]
    metrics: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "attacker": self.attacker,
            "defender": self.defender,
            "winner": self.winner,
            "metrics": self.metrics,
        }


@dataclass
class BattleListItemDTO:
    id: int
    attacker: str
    defender: str
    winner: Optional[str]
    created_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "attacker": self.attacker,
            "defender": self.defender,
            "winner": self.winner,
            "created_at": self.created_at,
        }


@dataclass
class PaginationDTO:
    page: int
    page_size: int
    total_count: int
    total_pages: int
    has_next: bool
    has_previous: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "page_size": self.page_size,
            "total_count": self.total_count,
            "total_pages": self.total_pages,
            "has_next": self.has_next,
            "has_previous": self.has_previous,
        }


@dataclass
class BattleListResponseDTO:
    results: List[BattleListItemDTO]
    pagination: PaginationDTO

    def to_dict(self) -> Dict[str, Any]:
        return {
            "results": [item.to_dict() for item in self.results],
            "pagination": self.pagination.to_dict(),
        }
