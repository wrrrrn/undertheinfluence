# UnderTheInfluence

UnderTheInfluence is a web application that tracks lobbying influence in UK politics. It aggregates data from multiple sources into a unified database based on the [Popolo open government data specification](http://www.popoloproject.com/).

## Current Status (January 2026)

| Component | Version |
|-----------|---------|
| Django | 6.0.1 |
| Python | 3.12 |
| Wagtail CMS | 7.2.x |
| PostgreSQL | 15 |
| Frontend | React 18 + Vite 5 (Islands Architecture) |

## Data Sources

| Source | Status | Description |
|--------|--------|-------------|
| [ParlParse](http://parser.theyworkforyou.com) | Working | MPs, Lords, ministerial appointments |
| [GOV.UK](https://www.gov.uk) | Working | Ministerial meetings transparency data |
| [MPs' Register of Interests](https://publications.parliament.uk) | Working | Financial interests |
| [Companies House](https://www.companieshouse.gov.uk) | Working | Company data enrichment |
| [Electoral Commission](http://search.electoralcommission.org.uk) | Broken | API changed, needs fixing |
| [APPC](http://www.appc.org.uk) | Broken | Site defunct (merged with PRCA 2018) |

## Quick Start (Docker)

```bash
# Clone the repository
git clone https://github.com/whoslobbying/undertheinfluence.git
cd undertheinfluence

# Copy environment template
cp .env.example .env

# Start all services
docker compose up -d

# Run migrations
docker compose exec api python manage.py migrate

# Create admin user
docker compose exec api python manage.py createsuperuser

# Access the application
open http://localhost:8000
```

## Import Data

```bash
# Import politicians (MPs and Lords)
docker compose exec api python manage.py import_parlparse --since 2010

# Import ministerial appointments
docker compose exec api python manage.py import_ministers --since 2010

# Import MPs' Register of Interests
docker compose exec api python manage.py import_mpsinterests --since 1996

# Import ministerial meetings
docker compose exec api python manage.py import_ministerial_meetings --department all --since 2024

# Enrich with Companies House data
docker compose exec api python manage.py enrich_companies_house --category lobbying_agency
```

## Documentation

| Document | Description |
|----------|-------------|
| [CLAUDE.md](CLAUDE.md) | Project setup and Claude Code instructions |
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/CURRENT_STATE.md](docs/CURRENT_STATE.md) | Feature inventory and status |
| [docs/systems-architecture.md](docs/systems-architecture.md) | Architecture reference |
| [docs/data-models.md](docs/data-models.md) | Data model reference |
| [docs/DATA_IMPORT_GUIDE.md](docs/DATA_IMPORT_GUIDE.md) | Import procedures |

## Development

```bash
# View logs
docker compose logs -f api

# Run Django shell
docker compose exec api python manage.py shell

# Run management commands
docker compose exec api python manage.py <command>

# Restart after code changes
docker compose restart api
```

## Deployment

See: https://github.com/spudmind/uti-deploy

## License

This project is open source.
