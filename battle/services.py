import logging

import requests
from django.core.cache import cache
from django.db import transaction

from .constants import (
    ATTACKER_STAT_WEIGHTS,
    BASE_EXPERIENCE_MULTIPLIER,
    DEFENDER_STAT_WEIGHTS,
    POKEAPI_BASE,
    STAT_CHANGE_FACTOR,
    TYPE_COUNT_BONUS,
)
from .dto import BattleResultDTO, PokeAPIPokemonDTO
from .logging_utils import format_message
from .models import Pokemon, PokemonAbility, PokemonStat, PokemonType


class PokeAPIClient:
    def __init__(
        self,
        base_url: str | None = None,
        cache_timeout_seconds: int = 3600,
        session: requests.Session | None = None,
    ):
        self.base_url = base_url or POKEAPI_BASE
        self.cache_timeout_seconds = cache_timeout_seconds
        self.session = session or requests

    def fetch_pokemon(self, name: str) -> PokeAPIPokemonDTO:
        cache_key = f"pokeapi:{name.lower()}"
        cached = cache.get(cache_key)
        if cached:
            return PokeAPIPokemonDTO.from_api_json(cached)
        resp = self.session.get(f"{self.base_url}/pokemon/{name.lower()}", timeout=10)
        if resp.status_code != 200:
            raise ValueError(f"Pokemon '{name}' not found")
        data = resp.json()
        cache.set(cache_key, data, timeout=self.cache_timeout_seconds)
        return PokeAPIPokemonDTO.from_api_json(data)

    def fetch_stat_details(self, stat_url: str) -> dict:
        """Fetch stat details to get affecting_moves with stat changes."""
        cache_key = f"pokeapi:stat:{stat_url}"
        cached = cache.get(cache_key)
        if cached:
            return cached
        resp = self.session.get(stat_url, timeout=10)
        if resp.status_code != 200:
            return {}
        data = resp.json()
        cache.set(cache_key, data, timeout=self.cache_timeout_seconds)
        return data

    def get_stat_change_value(self, stat_url: str) -> int:
        """Get the stat change value from affecting moves (both increase and decrease).

        Returns positive for increase moves, negative for decrease moves.
        """
        stat_data = self.fetch_stat_details(stat_url)
        if not stat_data:
            return 0

        affecting_moves = stat_data.get("affecting_moves", {})
        increase_moves = affecting_moves.get("increase", [])
        decrease_moves = affecting_moves.get("decrease", [])

        # Prefer increase moves if available
        if increase_moves:
            return increase_moves[0].get("change", 0)

        # Otherwise use decrease moves (as negative)
        if decrease_moves:
            return -decrease_moves[0].get("change", 0)

        return 0


class PokemonService:
    def __init__(self, client: PokeAPIClient | None = None):
        self.client = client or PokeAPIClient()
        self.logger = logging.getLogger("battle.services.pokemon")

    def upsert_pokemon_from_api(self, name: str) -> Pokemon:
        data = self.client.fetch_pokemon(name)
        stats = data.stats
        stat_urls = data.stat_urls
        types = data.types
        abilities = data.abilities

        pokemon, created = Pokemon.objects.update_or_create(
            name=data.name,
            defaults={
                "pokeapi_id": data.id,
                "base_experience": data.base_experience,
                "height": data.height,
                "weight": data.weight,
            },
        )

        # Update related data properly instead of delete/recreate
        with transaction.atomic():
            # Update stats with URLs
            for stat_name, stat_value in stats.items():
                stat_url = stat_urls.get(stat_name, "")
                PokemonStat.objects.update_or_create(
                    pokemon=pokemon,
                    name=stat_name,
                    defaults={"base_stat": stat_value, "stat_url": stat_url},
                )

            # Update types
            for type_name in types:
                PokemonType.objects.get_or_create(pokemon=pokemon, name=type_name)

            # Update abilities
            for ability_name in abilities:
                PokemonAbility.objects.get_or_create(pokemon=pokemon, name=ability_name)

            # Remove stats/types/abilities that are no longer present
            PokemonStat.objects.filter(pokemon=pokemon).exclude(name__in=stats.keys()).delete()
            PokemonType.objects.filter(pokemon=pokemon).exclude(name__in=types).delete()
            PokemonAbility.objects.filter(pokemon=pokemon).exclude(name__in=abilities).delete()

        if created:
            self.logger.info(
                format_message("Pokemon created", name=pokemon.name, pokeapi_id=pokemon.pokeapi_id)
            )
        else:
            self.logger.debug(
                format_message("Pokemon updated", name=pokemon.name, pokeapi_id=pokemon.pokeapi_id)
            )
        return pokemon


class BattleService:
    def __init__(self, algorithm_version: str = "v1", api_client: PokeAPIClient | None = None):
        self.algorithm_version = algorithm_version
        self.api_client = api_client or PokeAPIClient()
        self.logger = logging.getLogger("battle.services.battle")

    def apply_stat_changes(self, pokemon: Pokemon, base_stats: dict) -> dict:
        """Apply stat changes from PokeAPI affecting_moves at battle time.

        Applies both increases and decreases from affecting_moves.
        """
        modified_stats = base_stats.copy()

        for stat in pokemon.stats.all():  # type: ignore[attr-defined]
            if stat.stat_url:
                change = self.api_client.get_stat_change_value(stat.stat_url)
                if change != 0:
                    # Apply the change using configured factor
                    multiplier = 1.0 + (change * STAT_CHANGE_FACTOR)
                    modified_stats[stat.name] = int(base_stats[stat.name] * multiplier)

        return modified_stats

    def calculate_pokemon_score(
        self, pokemon: Pokemon, stat_weights: dict, opponent_types_count: int
    ) -> tuple[float, dict, dict]:
        """Calculate score for a single Pokemon.

        Returns:
            (score, modified_stats, stat_changes)
        """
        # Get base stats
        base_stats = {s.name: s.base_stat for s in pokemon.stats.all()}  # type: ignore[attr-defined]

        # Apply stat changes from PokeAPI
        modified_stats = self.apply_stat_changes(pokemon, base_stats)

        # Calculate base score using stat weights
        score = sum(
            modified_stats.get(stat_name, 0) * weight for stat_name, weight in stat_weights.items()
        )

        # Apply type bonus
        pokemon_types_count = pokemon.types.count()  # type: ignore[attr-defined]
        type_bonus = max(0, pokemon_types_count - opponent_types_count) * TYPE_COUNT_BONUS
        score += type_bonus

        # Apply experience bonus
        score += (pokemon.base_experience or 0) * BASE_EXPERIENCE_MULTIPLIER

        # Calculate stat changes for metrics
        stat_changes = {
            k: modified_stats[k] - base_stats[k]
            for k in modified_stats
            if modified_stats[k] != base_stats[k]
        }

        return score, modified_stats, stat_changes

    def compute_battle(self, attacker: Pokemon, defender: Pokemon) -> tuple[Pokemon | None, dict]:
        # Get type counts for bonuses
        attacker_types_count = attacker.types.count()  # type: ignore[attr-defined]
        defender_types_count = defender.types.count()  # type: ignore[attr-defined]

        # Calculate scores for both Pokemon
        attacker_score, _, attacker_changes = self.calculate_pokemon_score(
            attacker, ATTACKER_STAT_WEIGHTS, defender_types_count
        )
        defender_score, _, defender_changes = self.calculate_pokemon_score(
            defender, DEFENDER_STAT_WEIGHTS, attacker_types_count
        )

        metrics = {
            "attacker_score": attacker_score,
            "defender_score": defender_score,
            "attacker_stat_changes": attacker_changes,
            "defender_stat_changes": defender_changes,
            "algorithm_version": self.algorithm_version,
        }

        if abs(attacker_score - defender_score) < 1e-6:
            return None, metrics

        winner = attacker if attacker_score > defender_score else defender
        return winner, metrics

    def compute_battle_result(self, attacker: Pokemon, defender: Pokemon) -> BattleResultDTO:
        winner, metrics = self.compute_battle(attacker, defender)
        return BattleResultDTO(
            winner_name=winner.name if winner else None,
            metrics=metrics,
            algorithm_version=self.algorithm_version,
        )
