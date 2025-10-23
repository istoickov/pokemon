from django.db import models


class Pokemon(models.Model):
    name = models.CharField(max_length=64, unique=True)
    pokeapi_id = models.PositiveIntegerField(null=True, blank=True)
    base_experience = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    weight = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class PokemonStat(models.Model):
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="stats")
    name = models.CharField(max_length=64)
    base_stat = models.PositiveIntegerField()
    stat_url = models.URLField(max_length=256, blank=True, default="")

    class Meta:
        unique_together = ("pokemon", "name")

    def __str__(self) -> str:
        return f"{self.pokemon.name}:{self.name}={self.base_stat}"


class PokemonType(models.Model):
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="types")
    name = models.CharField(max_length=64)

    class Meta:
        unique_together = ("pokemon", "name")

    def __str__(self) -> str:
        return f"{self.pokemon.name}:{self.name}"


class PokemonAbility(models.Model):
    pokemon = models.ForeignKey(Pokemon, on_delete=models.CASCADE, related_name="abilities")
    name = models.CharField(max_length=64)

    class Meta:
        unique_together = ("pokemon", "name")

    def __str__(self) -> str:
        return f"{self.pokemon.name}:{self.name}"


class Battle(models.Model):
    attacker = models.ForeignKey(
        Pokemon, on_delete=models.CASCADE, related_name="battles_as_attacker"
    )
    defender = models.ForeignKey(
        Pokemon, on_delete=models.CASCADE, related_name="battles_as_defender"
    )
    winner = models.ForeignKey(
        Pokemon, on_delete=models.SET_NULL, null=True, blank=True, related_name="wins"
    )
    algorithm_version = models.CharField(max_length=32, default="v1")
    raw_metrics = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        winner_name = self.winner.name if self.winner else "draw"
        return f"{self.attacker.name} vs {self.defender.name} -> {winner_name}"
