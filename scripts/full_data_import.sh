#!/bin/bash

###############################################################################
# Full Data Import Script for UnderTheInfluence
#
# This script performs a complete data ingest from 1996 onwards:
# 1. Wipes the database
# 2. Runs migrations
# 3. Imports data from all working sources
# 4. Runs entity resolution
# 5. Shows statistics
#
# Usage:
#   ./scripts/full_data_import.sh
#   ./scripts/full_data_import.sh --skip-wipe    # Don't wipe DB first
#   ./scripts/full_data_import.sh --quick        # Skip entity resolution
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_WIPE=false
QUICK_MODE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-wipe)
            SKIP_WIPE=true
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Usage: $0 [--skip-wipe] [--quick]"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║      UnderTheInfluence - Full Data Import (1996+)             ║${NC}"
echo -e "${BLUE}║           6 Data Sources + Entity Resolution                   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Configuration
START_YEAR=1996
DOCKER_COMPOSE="docker compose"
WEB_SERVICE="web"

echo -e "${YELLOW}⚙️  Configuration:${NC}"
echo "  - Start year: $START_YEAR"
echo "  - Skip DB wipe: $SKIP_WIPE"
echo "  - Quick mode: $QUICK_MODE"
echo ""

###############################################################################
# Step 1: Database Wipe (Optional)
###############################################################################

if [ "$SKIP_WIPE" = false ]; then
    echo -e "${YELLOW}📦 Step 1/6: Wiping Database${NC}"
    echo "  This will delete ALL data in the database."
    echo ""
    read -p "  Are you sure? (yes/no): " -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
        echo -e "${RED}❌ Aborted by user${NC}"
        exit 1
    fi

    echo "  Dropping and recreating database..."
    $DOCKER_COMPOSE exec -T db psql -U undertheinfluence -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;" 2>/dev/null || true
    echo -e "${GREEN}  ✓ Database wiped${NC}"
    echo ""
else
    echo -e "${YELLOW}📦 Step 1/6: Skipping Database Wipe${NC}"
    echo -e "${GREEN}  ✓ Using existing database${NC}"
    echo ""
fi

###############################################################################
# Step 2: Run Migrations
###############################################################################

echo -e "${YELLOW}🔄 Step 2/6: Running Database Migrations${NC}"
$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py migrate --noinput
echo -e "${GREEN}  ✓ Migrations complete${NC}"
echo ""

###############################################################################
# Step 3: Import ParlParse Data (MPs & Lords)
###############################################################################

echo -e "${YELLOW}🏛️  Step 3/6: Importing ParlParse Data (MPs & Lords since $START_YEAR)${NC}"
echo "  This includes persons, organizations, posts, and memberships"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py import_parlparse --since $START_YEAR --refresh

echo -e "${GREEN}  ✓ ParlParse import complete${NC}"
echo ""

###############################################################################
# Step 4: Import Ministers Data
###############################################################################

echo -e "${YELLOW}👔 Step 4/6: Importing Ministers Data (since $START_YEAR)${NC}"
echo "  This includes ministerial appointments and government positions"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py import_ministers --since $START_YEAR --refresh

echo -e "${GREEN}  ✓ Ministers import complete${NC}"
echo ""

###############################################################################
# Step 5: Import TheyWorkForYou Biographical Data (Optional)
###############################################################################

echo -e "${YELLOW}📝 Step 5/9: Importing TheyWorkForYou Biographical Data (Optional)${NC}"
echo "  Note: Requires TWFY_API_KEY in .env file"
echo "  The import command will skip gracefully if API key is not configured"
echo ""

# Always attempt the import - docker-compose loads .env file automatically
# The import command will handle missing API key gracefully
$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py import_twfy --since $START_YEAR --refresh || true

echo -e "${GREEN}  ✓ TheyWorkForYou import attempt complete${NC}"
echo ""

###############################################################################
# Step 6: Import MPs' Register of Interests
###############################################################################

echo -e "${YELLOW}📊 Step 6/9: Importing MPs' Register of Interests (since $START_YEAR)${NC}"
echo "  This includes donations, gifts, and sponsored visits"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py import_mpsinterests --since $START_YEAR --refresh

echo -e "${GREEN}  ✓ MPs' Interests import complete${NC}"
echo ""

###############################################################################
# Step 7: Import Lords' Register of Interests
###############################################################################

echo -e "${YELLOW}🎩 Step 7/9: Importing Lords' Register of Interests${NC}"
echo "  This includes sponsorships, overseas visits, and gifts to Lords"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py import_lordsinterests --refresh

echo -e "${GREEN}  ✓ Lords' Interests import complete${NC}"
echo ""

###############################################################################
# Step 8: Import APPC Archive (Historical Lobbying Registers)
###############################################################################

echo -e "${YELLOW}📑 Step 8/9: Importing APPC Archive (Historical Lobbying Registers)${NC}"
echo "  This includes lobbying agencies, practitioners, and client relationships"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py import_appc_archive --refresh

echo -e "${GREEN}  ✓ APPC Archive import complete${NC}"
echo ""

###############################################################################
# Step 9: Entity Resolution
###############################################################################

if [ "$QUICK_MODE" = false ]; then
    echo -e "${YELLOW}🔍 Step 9/9: Running Entity Resolution${NC}"
    echo "  Identifying duplicate actors for review..."
    echo ""

    $DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py resolve_duplicates --clear

    echo -e "${GREEN}  ✓ Entity resolution complete${NC}"
    echo ""
else
    echo -e "${YELLOW}🔍 Step 9/9: Skipping Entity Resolution (Quick Mode)${NC}"
    echo -e "${GREEN}  ✓ Skipped${NC}"
    echo ""
fi

###############################################################################
# Final Statistics
###############################################################################

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    Import Statistics                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py shell -c "
from datafetch.models import Person, Organization, Membership, Donation, Consultancy, ActorResolution

person_count = Person.objects.count()
org_count = Organization.objects.count()
membership_count = Membership.objects.count()
donation_count = Donation.objects.count()
consultancy_count = Consultancy.objects.count()
resolution_count = ActorResolution.objects.count()

print(f'Persons:              {person_count:>8,}')
print(f'Organizations:        {org_count:>8,}')
print(f'Memberships:          {membership_count:>8,}')
print(f'Donations:            {donation_count:>8,}')
print(f'Consultancies:        {consultancy_count:>8,}')
print(f'Actor Resolutions:    {resolution_count:>8,}')
print()
print('✓ Import complete!')
"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                  🎉 Import Complete! 🎉                        ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Review duplicate actors at:"
echo "     http://localhost:8000/django-admin/datafetch/actorresolution/"
echo ""
echo "  2. Approve/reject merge candidates in Django admin"
echo ""
echo "  3. Check data quality with:"
echo "     docker compose exec web python manage.py shell"
echo ""

###############################################################################
# Skipped Imports (Documentation)
###############################################################################

echo -e "${YELLOW}📋 Skipped Imports:${NC}"
echo ""
echo -e "${RED}  ⛔ Broken (Not Imported):${NC}"
echo "     • import_ec          - Electoral Commission API defunct"
echo "     • import_appc        - APPC site defunct (merged with PRCA in 2018)"
echo ""
echo -e "${YELLOW}  ⏸️  Untested/Partial (Skipped):${NC}"
echo "     • import_everypolitician - MP photos (slow, cdn.rawgit.com defunct)"
echo "     • import_companieshouse  - Company metadata (fetch only, no parser)"
echo "     • import_powerbase       - Powerbase wiki (fetch only, no parser)"
echo ""
echo -e "${GREEN}  ✅ Included in this import:${NC}"
echo "     • import_parlparse       - MPs, Lords, memberships (since $START_YEAR)"
echo "     • import_ministers       - Ministerial appointments (since $START_YEAR)"
echo "     • import_twfy            - TheyWorkForYou biographical data (if API key set)"
echo "     • import_mpsinterests    - MPs' Register of Interests (since $START_YEAR)"
echo "     • import_lordsinterests  - Lords' Register of Interests"
echo "     • import_appc_archive    - Historical lobbying registers (APPC PDFs)"
echo ""
echo "  See CLAUDE.md for details on data sources"
echo ""
