import logging

from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from battle.constants import DEFAULT_PAGE, DEFAULT_PAGE_SIZE
from battle.dto import BattleCreateResponseDTO, BattleListItemDTO, BattleListResponseDTO
from battle.logging_utils import format_message
from battle.models import Battle
from battle.paginator import Paginator
from battle.services import BattleService, PokemonService

logger = logging.getLogger("battle.views")


class BattleViewSet(viewsets.ViewSet):
    @extend_schema(
        summary="List battles",
        description="Get a paginated list of recent battles",
        responses={200: BattleListResponseDTO},
    )
    def list(self, request):
        page = int(request.query_params.get("page", DEFAULT_PAGE))
        page_size = int(request.query_params.get("page_size", DEFAULT_PAGE_SIZE))

        qs = Battle.objects.select_related("attacker", "defender", "winner").all()
        paginator = Paginator(qs, page=page, page_size=page_size)

        battles = paginator.get_page_items()
        pagination_info = paginator.get_pagination_info()

        items = [
            BattleListItemDTO(
                id=b.id,
                attacker=b.attacker.name,
                defender=b.defender.name,
                winner=b.winner.name if b.winner else None,
                created_at=b.created_at.isoformat(),
            )
            for b in battles
        ]

        response_data = {"results": [item.to_dict() for item in items], **pagination_info.to_dict()}
        return Response(response_data)

    @extend_schema(
        summary="Simulate a battle",
        description="Create a battle between two Pokémon and determine the winner",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "attacker": {"type": "string", "example": "pikachu"},
                    "defender": {"type": "string", "example": "bulbasaur"},
                },
                "required": ["attacker", "defender"],
            }
        },
        responses={
            201: BattleCreateResponseDTO,
            400: {"description": "Bad request - missing attacker or defender"},
            404: {"description": "Pokémon not found"},
            500: {"description": "Internal server error"},
        },
    )
    @action(detail=False, methods=["post"], url_path="battle")
    def battle(self, request):
        name1 = request.data.get("attacker")
        name2 = request.data.get("defender")

        if not name1 or not name2:
            return Response(
                {"detail": "attacker and defender are required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                pokemon_service = PokemonService()
                battle_service = BattleService()
                p1 = pokemon_service.upsert_pokemon_from_api(name1)
                p2 = pokemon_service.upsert_pokemon_from_api(name2)
                winner, metrics = battle_service.compute_battle(p1, p2)
                battle = Battle.objects.create(
                    attacker=p1, defender=p2, winner=winner, raw_metrics=metrics
                )

                dto = BattleCreateResponseDTO(
                    id=battle.id,
                    attacker=p1.name,
                    defender=p2.name,
                    winner=winner.name if winner else None,
                    metrics=metrics,
                )
                logger.info(
                    format_message(
                        "Battle created",
                        battle_id=battle.id,
                        attacker=p1.name,
                        defender=p2.name,
                        winner=winner.name if winner else None,
                    )
                )
                return Response(dto.to_dict(), status=status.HTTP_201_CREATED)
        except ValueError as e:
            logger.warning(
                format_message(
                    "Item cannot be found",
                    detail=str(e),
                    attacker=name1,
                    defender=name2,
                )
            )
            return Response({"detail": str(e)}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            logger.exception(
                format_message("Internal server error", attacker=name1, defender=name2)
            )
            return Response(
                {"detail": "Internal error"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
