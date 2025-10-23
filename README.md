# Pokémon Battle API

A Django REST API for simulating Pokémon battles with data from PokeAPI.co. Features include battle simulation, relational database models, Redis caching, and comprehensive Swagger documentation.

## Features

- 🎮 **Battle Simulation**: Simulate battles between two Pokémon with algorithm-based winner determination
- 📊 **Relational Data Models**: Pokemon stats, types, and abilities stored in separate tables
- ⚡ **Redis Caching**: PokeAPI responses cached for 1 hour
- 📖 **Swagger Documentation**: Interactive API docs at `/api/docs/`
- 🔄 **Pagination**: Paginated battle history with customizable page size
- 📝 **Structured Logging**: Unified logging format with context
- 🐳 **Docker Support**: Full containerization with Docker Compose
- 🧪 **Type Safety**: MyPy type checking configured
- 🎨 **Code Quality**: Ruff linting and formatting

## Quickstart (Docker)

```bash
# Start the full stack (Django + Postgres + Redis)
make up

# Or manually
docker compose up --build
```

**API Access:**
- API Base: http://localhost:8000/api/
- Swagger UI: http://localhost:8000/api/docs/
- ReDoc: http://localhost:8000/api/redoc/

## Local Development (without Docker)

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export POSTGRES_HOST=localhost
export POSTGRES_DB=pokemon
export POSTGRES_USER=postgres
export POSTGRES_PASSWORD=postgres
export REDIS_URL=redis://localhost:6379/1

# Run migrations and start server
python manage.py migrate
python manage.py runserver
```

## API Endpoints

### Simulate Battle
```http
POST /api/battles/battle/
Content-Type: application/json

{
  "attacker": "pikachu",
  "defender": "bulbasaur"
}
```

**Response (201 Created):**
```json
{
  "id": 1,
  "attacker": "pikachu",
  "defender": "bulbasaur",
  "winner": "pikachu",
  "metrics": {
    "attacker_score": 187.6,
    "defender_score": 165.3,
    "algorithm_version": "v1"
  }
}
```

### List Battles (Paginated)
```http
GET /api/battles/?page=1&page_size=20
```

**Response (200 OK):**
```json
{
  "results": [
    {
      "id": 1,
      "attacker": "pikachu",
      "defender": "bulbasaur",
      "winner": "pikachu",
      "created_at": "2025-10-22T11:15:12.120Z"
    }
  ],
  "page": 1,
  "page_size": 20,
  "total_count": 150,
  "total_pages": 8,
  "has_next": true,
  "has_previous": false
}
```

## Data Model

### Pokemon
- `name` (CharField, unique)
- `pokeapi_id` (PositiveIntegerField)
- `base_experience`, `height`, `weight` (PositiveIntegerField)
- Related models: `PokemonStat`, `PokemonType`, `PokemonAbility`

### PokemonStat
- `pokemon` (ForeignKey)
- `name` (CharField) - e.g., "attack", "defense"
- `base_stat` (PositiveIntegerField)

### PokemonType
- `pokemon` (ForeignKey)
- `name` (CharField) - e.g., "electric", "grass"

### PokemonAbility
- `pokemon` (ForeignKey)
- `name` (CharField) - e.g., "static", "overgrow"

### Battle
- `attacker`, `defender`, `winner` (ForeignKey to Pokemon)
- `algorithm_version` (CharField)
- `raw_metrics` (JSONField)
- `created_at` (DateTimeField)

## Battle Algorithm (v1)

The battle winner is determined by computing weighted scores with **dynamic stat boosts from PokeAPI**:

### Stat Modification (Using PokeAPI stat.change)
For each Pokémon stat, the algorithm:
1. Fetches stat details from the stored stat URL (e.g., `https://pokeapi.co/api/v2/stat/1/`)
2. Looks at `affecting_moves` → `increase` and `decrease` arrays
3. Takes the `change` value from the first move (typically 1-3)
4. Applies multiplier: `1.0 + (change × 0.25)`
   - change=2 → 1.5× boost
   - change=1 → 1.25× boost
   - change=-1 → 0.75× reduction
   - change=-2 → 0.5× (halved)
   - change=-4 → 0.0× (never reaches zero due to 0.25 factor)

**Example:** If "Swords Dance" has change=2 for attack, and Pikachu's attack is 55:
- Modified attack = 55 × 1.5 = 82

**Example:** If "Growl" has change=-1 for attack, and opponent's attack is 60:
- Modified attack = 60 × 0.75 = 45

### Score Calculation
**Attacker Score (Offensive):**
```
score = 1.2 × modified_attack + 1.1 × modified_special-attack + 1.0 × modified_speed
```

**Defender Score (Defensive):**
```
score = 1.2 × modified_defense + 1.1 × modified_special-defense + 1.0 × modified_hp
```

### Additional Factors
- Type advantage: +5 per extra type compared to opponent
- Experience bonus: +0.05 × base_experience

### Winner Determination
The Pokémon with the higher score wins. Near-equal scores (< 0.000001 difference) result in a draw.

### Battle Metrics
Each battle returns:
- `attacker_score` / `defender_score`: Final calculated scores
- `attacker_stat_changes` / `defender_stat_changes`: Which stats were modified and by how much
- `algorithm_version`: Algorithm version used

**Rationale:**
- **Real PokeAPI data**: Uses actual `stat.change` values from `affecting_moves.increase`
- **Deterministic per stat**: Same stat URL always gives same boost
- **Cached**: Stat details are cached in Redis to minimize API calls
- **Balanced**: Change multipliers prevent extreme outcomes
- **Transparent**: Metrics show exactly what changed

This leverages the PokeAPI `stat.change` field as suggested in requirements.

## Architecture

### Services
- **PokeAPIClient**: Fetches and caches Pokémon data from PokeAPI
- **PokemonService**: Manages Pokemon records with related stats/types/abilities
- **BattleService**: Implements battle algorithm and scoring

### DTOs
- Structured data transfer objects for API requests/responses
- `BattleCreateResponseDTO`, `BattleListItemDTO`, `PaginationDTO`

### Logging
- Unified logging format with `format_message()` helper
- Structured context in all log messages
- Examples: "Battle created", "Item cannot be found", "Internal server error"

### Caching
- Redis backend via django-redis
- PokeAPI responses cached for 1 hour
- Cache key format: `pokeapi:{pokemon_name}`

## Development Tools

### Makefile Commands

```bash
# Install dev dependencies
make install-dev

# Linting and formatting
make ruff-check      # Check code quality
make ruff-fix        # Auto-fix issues

# Type checking
make mypy            # Run type checker

# Docker
make up              # Start stack
make build           # Build images
make down            # Stop stack
make logs            # View logs
```

### Configuration Files
- `pyproject.toml` - Ruff and MyPy configuration
- `.env` - Environment variables for Docker
- `docker-compose.yml` - Multi-container setup

## Testing

```bash
# Run all tests
python manage.py test

# Run with coverage (if installed)
pytest --cov=battle
```

Tests cover:
- Battle algorithm logic
- API endpoints
- Service layer
- Pagination

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DJANGO_DEBUG` | `1` | Debug mode |
| `DJANGO_ALLOWED_HOSTS` | `*` | Allowed hosts |
| `DJANGO_LOG_LEVEL` | `INFO` | Logging level |
| `POSTGRES_DB` | `pokemon` | Database name |
| `POSTGRES_USER` | `postgres` | Database user |
| `POSTGRES_PASSWORD` | `postgres` | Database password |
| `POSTGRES_HOST` | `localhost` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `REDIS_URL` | `redis://localhost:6379/1` | Redis connection |

## Error Handling

- **400 Bad Request**: Missing required fields (attacker/defender)
- **404 Not Found**: Pokémon not found in PokeAPI
- **500 Internal Server Error**: Unexpected errors with exception logging

## Tech Stack

- **Framework**: Django 5.1.2 with Django REST Framework 3.15.2
- **Database**: PostgreSQL 16 with psycopg2
- **Cache**: Redis 7 with django-redis
- **API Docs**: drf-spectacular (Swagger/OpenAPI)
- **HTTP Client**: requests 2.32.3
- **Type Checking**: MyPy 1.13.0 with django-stubs
- **Linting**: Ruff 0.6.9
- **Containerization**: Docker & Docker Compose

## Project Structure

```
pokemon/
├── battle/                 # Main app
│   ├── models.py          # Database models
│   ├── services.py        # Business logic
│   ├── views.py           # API endpoints
│   ├── dto.py             # Data transfer objects
│   ├── paginator.py       # Pagination logic
│   ├── logging_utils.py   # Logging helpers
│   └── tests.py           # Unit tests
├── config/                # Django settings
│   ├── settings.py
│   └── urls.py
├── requirements.txt       # Python dependencies
├── dev-requirements.txt   # Dev tools
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── README.md
```

## License

This project is for educational/evaluation purposes.

## External Dependencies

- **PokeAPI** (https://pokeapi.co/) - Pokémon data source (assumed reliable)
