# Pokémon Battle API

A Django REST API for simulating Pokémon battles with data from PokeAPI.co. Features include battle simulation, relational database models, Redis caching, and comprehensive Swagger documentation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Features](#features)
- [Quickstart (Docker)](#quickstart-docker)
- [Local Development](#local-development-without-docker)
- [API Endpoints](#api-endpoints)
- [Data Model](#data-model)
- [Battle Algorithm](#battle-algorithm-v1)
- [Architecture](#architecture)
- [Development Workflow](#development-workflow)
- [Development Tools](#development-tools)
- [Testing](#testing)
- [Environment Variables](#environment-variables)
- [Error Handling](#error-handling)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

## Prerequisites

- **Python**: 3.12+
- **Docker**: 20.10+ (if using Docker setup)
- **Docker Compose**: 2.0+ (if using Docker setup)

For local development without Docker:
- **PostgreSQL**: 16+
- **Redis**: 7+

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

1. **Create environment file** - Create a `.env` file in the project root with the following content:
```bash
# Database
POSTGRES_DB=pokemon
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_HOST=db
POSTGRES_PORT=5432

# Redis
REDIS_URL=redis://redis:6379/1

# Django
DJANGO_DEBUG=1
DJANGO_ALLOWED_HOSTS=*
DJANGO_LOG_LEVEL=INFO
```

> **Note:** You can customize these values as needed. For local development without Docker, change `POSTGRES_HOST=db` to `POSTGRES_HOST=localhost`.

2. **Start the stack:**
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

3. **Try it out:**
```bash
# Simulate a battle between Pikachu and Charizard
curl -X POST http://localhost:8000/api/battles/battle/ \
  -H "Content-Type: application/json" \
  -d '{"attacker": "pikachu", "defender": "charizard"}'

# View battle history
curl http://localhost:8000/api/battles/
```

## Local Development (without Docker)

**Note:** Requires PostgreSQL and Redis running locally.

```bash
# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install dev dependencies (optional, for linting/type checking)
pip install -r dev-requirements.txt

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

## Development Workflow

Recommended workflow for making changes:

1. **Set up development environment:**
```bash
make install-dev  # Installs all dependencies including dev tools
```

2. **Make your changes** to the code

3. **Run quality checks:**
```bash
make ruff-check    # Check for linting issues
make ruff-format   # Format code
make mypy          # Type check
python manage.py test  # Run tests
```

4. **Test locally:**
```bash
make up  # Start Docker stack
# Or for local dev:
python manage.py runserver
```

5. **Verify changes** via Swagger UI at http://localhost:8000/api/docs/

## Development Tools

### Dev Dependencies

The `dev-requirements.txt` file includes:
- **ruff** (0.6.9) - Fast Python linter and formatter
- **mypy** (1.13.0) - Static type checker
- **django-stubs** (5.1.1) - Type stubs for Django
- **types-requests** - Type stubs for requests library

Install with: `pip install -r dev-requirements.txt`

### Makefile Commands

```bash
# Install dev dependencies
make install-dev      # Install both requirements.txt and dev-requirements.txt

# Linting and formatting
make ruff-check       # Check code quality issues
make ruff-fix         # Auto-fix linting issues
make ruff-format      # Format code with Ruff

# Type checking
make mypy             # Run MyPy type checker

# Docker
make up               # Start full stack (Django + Postgres + Redis)
make build            # Build Docker images
make down             # Stop and remove containers
make logs             # View container logs (follow mode)
```

### Configuration Files
- `pyproject.toml` - Ruff and MyPy configuration
- `.env` - Environment variables for Docker
- `docker-compose.yml` - Multi-container setup
- `requirements.txt` - Production dependencies
- `dev-requirements.txt` - Development tools

## Testing

```bash
# Run all tests with Django's test runner
python manage.py test

# Run specific test module
python manage.py test battle.tests

# Run with verbose output
python manage.py test --verbosity=2
```

Tests cover:
- Battle algorithm logic
- API endpoints
- Service layer
- Pagination
- Error handling

**Note:** The project uses Django's built-in test framework. To add coverage reporting, install `coverage` and run:
```bash
pip install coverage
coverage run --source='.' manage.py test
coverage report
```

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
│   ├── constants.py       # Application constants
│   └── tests.py           # Unit tests
├── config/                # Django settings
│   ├── settings.py
│   └── urls.py
├── requirements.txt       # Python dependencies
├── dev-requirements.txt   # Dev tools
├── pyproject.toml         # Tool configurations
├── Dockerfile
├── docker-compose.yml
├── Makefile
└── README.md
```

## Troubleshooting

### Docker Issues

**Problem:** `Cannot connect to the Docker daemon`
```bash
# Solution: Ensure Docker Desktop is running
# macOS: Open Docker Desktop app
# Linux: sudo systemctl start docker
```

**Problem:** Port already in use (8000, 5432, or 6379)
```bash
# Solution: Stop conflicting services or change ports in docker-compose.yml
docker ps  # Check what's running
lsof -i :8000  # See what's using port 8000
```

**Problem:** Database connection errors
```bash
# Solution: Recreate containers with fresh volumes
make down
docker volume rm pokemon_pgdata
make up
```

### Local Development Issues

**Problem:** `ModuleNotFoundError`
```bash
# Solution: Ensure virtual environment is activated and dependencies installed
source .venv/bin/activate
pip install -r requirements.txt
```

**Problem:** Redis connection error
```bash
# Solution: Ensure Redis is running locally
# macOS: brew services start redis
# Linux: sudo systemctl start redis
redis-cli ping  # Should return "PONG"
```

**Problem:** PostgreSQL connection error
```bash
# Solution: Verify PostgreSQL is running and credentials match
# Check connection with:
psql -h localhost -U postgres -d pokemon
```

### API Issues

**Problem:** 404 when fetching Pokémon
```bash
# Solution: Ensure Pokémon name is lowercase and correct
# Valid: "pikachu", "charizard"
# Invalid: "Pikachu", "charzard"
```

**Problem:** PokeAPI rate limiting
```bash
# Solution: Redis caching should prevent this. Check Redis is working:
docker compose logs redis  # If using Docker
redis-cli GET pokeapi:pikachu  # Check if data is cached
```

## License

This project is for educational/evaluation purposes.

## External Dependencies

- **PokeAPI** (https://pokeapi.co/) - Pokémon data source (assumed reliable)
