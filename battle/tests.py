from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse

from .models import Pokemon, PokemonStat
from .services import BattleService


class BattleLogicTests(TestCase):
    def test_compute_battle_prefers_higher_attack(self):
        # Create Pokemon with related stats
        p1 = Pokemon.objects.create(name="p1", base_experience=200)
        PokemonStat.objects.create(pokemon=p1, name="attack", base_stat=100)
        PokemonStat.objects.create(pokemon=p1, name="special-attack", base_stat=50)
        PokemonStat.objects.create(pokemon=p1, name="speed", base_stat=50)
        PokemonStat.objects.create(pokemon=p1, name="defense", base_stat=50)
        PokemonStat.objects.create(pokemon=p1, name="special-defense", base_stat=50)
        PokemonStat.objects.create(pokemon=p1, name="hp", base_stat=50)

        p2 = Pokemon.objects.create(name="p2", base_experience=200)
        PokemonStat.objects.create(pokemon=p2, name="attack", base_stat=50)
        PokemonStat.objects.create(pokemon=p2, name="special-attack", base_stat=50)
        PokemonStat.objects.create(pokemon=p2, name="speed", base_stat=50)
        PokemonStat.objects.create(pokemon=p2, name="defense", base_stat=100)
        PokemonStat.objects.create(pokemon=p2, name="special-defense", base_stat=100)
        PokemonStat.objects.create(pokemon=p2, name="hp", base_stat=100)

        battle_service = BattleService()
        winner, metrics = battle_service.compute_battle(p1, p2)

        # p1 should win with higher attack stats
        self.assertEqual(winner, p2)
        self.assertIn("attacker_score", metrics)
        self.assertIn("defender_score", metrics)


class BattleApiTests(TestCase):
    @patch("battle.services.requests.get")
    def test_battle_endpoint(self, mock_get):
        # Fake PokeAPI responses
        def fake_poke(name, id, atk=55, sp_atk=50, spd=90, df=40, sp_df=50, hp=35):
            return {
                "id": id,
                "name": name,
                "base_experience": 100,
                "height": 4,
                "weight": 60,
                "stats": [
                    {"stat": {"name": "attack"}, "base_stat": atk},
                    {"stat": {"name": "special-attack"}, "base_stat": sp_atk},
                    {"stat": {"name": "speed"}, "base_stat": spd},
                    {"stat": {"name": "defense"}, "base_stat": df},
                    {"stat": {"name": "special-defense"}, "base_stat": sp_df},
                    {"stat": {"name": "hp"}, "base_stat": hp},
                ],
                "types": [{"type": {"name": "electric"}}],
                "abilities": [{"ability": {"name": "static"}}],
            }

        # Mock response objects
        mock_resp_pikachu = MagicMock()
        mock_resp_pikachu.status_code = 200
        mock_resp_pikachu.json.return_value = fake_poke("pikachu", 25)

        mock_resp_bulbasaur = MagicMock()
        mock_resp_bulbasaur.status_code = 200
        mock_resp_bulbasaur.json.return_value = fake_poke("bulbasaur", 1)

        mock_get.side_effect = [mock_resp_pikachu, mock_resp_bulbasaur]

        # Use the ViewSet action URL pattern
        url = reverse("battles-battle")
        resp = self.client.post(
            url,
            data={"attacker": "pikachu", "defender": "bulbasaur"},
            content_type="application/json",
        )

        self.assertEqual(resp.status_code, 201)
        resp_data = resp.json()
        self.assertIn("winner", resp_data)
        self.assertIn("attacker", resp_data)
        self.assertIn("defender", resp_data)
        self.assertIn("metrics", resp_data)


class PaginatorTests(TestCase):
    def setUp(self):
        # Create some test battles
        p1 = Pokemon.objects.create(name="pikachu")
        p2 = Pokemon.objects.create(name="bulbasaur")

        from .models import Battle

        for _i in range(25):
            Battle.objects.create(attacker=p1, defender=p2, winner=p1)

    def test_battle_list_pagination(self):
        url = reverse("battles-list")

        # Test first page
        resp = self.client.get(url + "?page=1&page_size=10")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()

        self.assertIn("results", data)
        self.assertEqual(len(data["results"]), 10)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["page_size"], 10)
        self.assertEqual(data["total_count"], 25)
        self.assertEqual(data["total_pages"], 3)
        self.assertTrue(data["has_next"])
        self.assertFalse(data["has_previous"])

        # Test second page
        resp = self.client.get(url + "?page=2&page_size=10")
        data = resp.json()
        self.assertEqual(len(data["results"]), 10)
        self.assertTrue(data["has_previous"])
