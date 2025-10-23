from django.contrib import admin

from battle.models import Battle, Pokemon


@admin.register(Pokemon)
class PokemonAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "pokeapi_id", "base_experience")
    search_fields = ("name",)


@admin.register(Battle)
class BattleAdmin(admin.ModelAdmin):
    list_display = ("id", "attacker", "defender", "winner", "created_at")
    search_fields = ("attacker__name", "defender__name", "winner__name")
