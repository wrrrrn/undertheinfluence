#!/bin/bash

###############################################################################
# Import Statistics Script for UnderTheInfluence
#
# Shows current database statistics for all imported data.
#
# Usage:
#   ./scripts/import_stats.sh
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

DOCKER_COMPOSE="docker compose"
WEB_SERVICE="web"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║              UnderTheInfluence - Import Statistics             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

$DOCKER_COMPOSE exec -T $WEB_SERVICE python manage.py shell -c "
from datafetch.models import Person, Organization, Membership, Donation, Consultancy, ActorResolution
from django.db.models import Count

# Basic counts
person_count = Person.objects.count()
org_count = Organization.objects.count()
membership_count = Membership.objects.count()
donation_count = Donation.objects.count()
consultancy_count = Consultancy.objects.count()
resolution_count = ActorResolution.objects.count()

print('${YELLOW}Record Counts:${NC}')
print(f'  Persons:              {person_count:>8,}')
print(f'  Organizations:        {org_count:>8,}')
print(f'  Memberships:          {membership_count:>8,}')
print(f'  Donations:            {donation_count:>8,}')
print(f'  Consultancies:        {consultancy_count:>8,}')
print(f'  Actor Resolutions:    {resolution_count:>8,}')
print()

# Organization breakdown by classification
print('${YELLOW}Organizations by Type:${NC}')
org_types = Organization.objects.values('classification').annotate(
    count=Count('id')
).order_by('-count')[:10]
for org_type in org_types:
    classification = org_type['classification'] or '(no classification)'
    print(f'  {classification:30} {org_type[\"count\"]:>8,}')
print()

# Duplicate counts
print('${YELLOW}Duplicate Detection:${NC}')
person_dupes = Person.objects.values('name').annotate(
    count=Count('id')
).filter(count__gt=1).count()
org_dupes = Organization.objects.values('name').annotate(
    count=Count('id')
).filter(count__gt=1).count()
print(f'  Persons with duplicate names:       {person_dupes:>8,}')
print(f'  Organizations with duplicate names: {org_dupes:>8,}')
print()

# Resolution breakdown
if resolution_count > 0:
    print('${YELLOW}Entity Resolutions by Decision:${NC}')
    resolutions = ActorResolution.objects.values('decision').annotate(
        count=Count('id')
    ).order_by('-count')
    for res in resolutions:
        decision = res['decision'] or '(pending)'
        print(f'  {decision:20} {res[\"count\"]:>8,}')
    print()

# Identifier counts
from datafetch.models import Identifier
identifier_count = Identifier.objects.count()
identifier_schemes = Identifier.objects.values('scheme').annotate(
    count=Count('id')
).order_by('-count')[:10]

print('${YELLOW}Identifiers:${NC}')
print(f'  Total identifiers:    {identifier_count:>8,}')
print()
print('  Top identifier schemes:')
for scheme in identifier_schemes:
    print(f'    {scheme[\"scheme\"]:40} {scheme[\"count\"]:>8,}')
print()
"

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Statistics Complete                         ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
