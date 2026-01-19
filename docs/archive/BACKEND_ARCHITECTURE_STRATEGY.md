# Backend Architecture Strategy

**Document Version:** 1.1
**Date:** January 14, 2026
**Phase:** 3.0 (Post Django 6.0.1 Modernization)
**Status:** Strategic Planning (Revised)

---

## Executive Summary

This document provides a comprehensive backend architecture strategy for Phase 3 of UnderTheInfluence, transitioning from data ingestion to presenting a meaningful lens on political influence in the UK. Based on extensive analysis of the current codebase, data analysis findings, and architectural documentation, this strategy identifies critical gaps, recommends specific technical improvements, and provides a prioritized implementation roadmap.

**Key Strategic Priorities:**

1. **Entity Resolution First:** The data's value is fundamentally limited by duplicate actors (e.g., "David Sainsbury" vs "David Sainsbury of Turville"). No visualization or API can compensate for fragmented identity.

2. **Party Affiliation Data Exists But Requires Temporal Queries:** The database contains 1.85 BILLION in donations to entities classified as "Political Party". However, aggregating individual MP donations by party affiliation requires temporal queries against the `PartyMembership` timeline, as MPs can switch parties.

3. **Concentration Analysis Requires Aggregation Infrastructure:** With 1.3% of donors controlling 65% of donation value, the backend must support efficient pre-computed aggregations, not real-time calculation.

4. **The API is Under-designed for the Use Case:** Current endpoints are CRUD-centric rather than analysis-centric. The frontend needs leaderboards, aggregates, and relationship summaries - not just entity lists.

---

## Part 1: Data Modeling Strategy

### 1.1 Critique of Current Popolo-Based Approach

**Strengths (Retain These):**

The Popolo foundation is architecturally sound:
- Polymorphic `Actor` model elegantly handles Person/Organization unified queries
- Generic relations for metadata (Identifiers, OtherNames, Sources) provide extensibility without schema bloat
- Dateframeable mixin with partial date support correctly models political data's inherent imprecision

**Weaknesses (Address These):**

| Issue | Impact | Severity |
|-------|--------|----------|
| No normalized name field | Cannot perform consistent lookups; duplicates proliferate | Critical |
| No denormalized party affiliation on Person | Temporal party queries are expensive without pre-computed data | High |
| Overloaded `classification` field on Organization | Trade unions, companies, parties all in one field without taxonomy | High |
| Source redundancy in Relationship model | Both URLField and GenericRelation; confusing and inconsistent | Medium |
| Donation.start_date property shadows inherited field | Breaks Dateframeable contract; confusing ORM behavior | Medium |
| CATEGORY_CHOICES/NATURE_CHOICES not enforced | No data integrity on donation types | Low |

### 1.2 Entity Resolution Architecture (Priority 1)

**The Core Problem:**

The data analysis revealed critical fragmentation:
- "David Sainsbury" and "David Sainsbury of Turville" are separate actors
- "Unite" vs "Unite the Union" create split statistics
- Identical organizations appear multiple times with slight name variations

#### 1.2.1 Weighted Alias System

**Critique Addressed:** The original normalization approach was too aggressive. Stripping "Unite the Union" to "unite union" risks false positives since "Unite" is a common word. The solution is a **confidence-weighted alias system** that distinguishes between high-confidence exact matches and lower-confidence normalized matches.

**Resolution Hierarchy with Confidence Scoring:**

```
Level 1: Identifier Match (Confidence: 1.0 - Auto-merge safe)
   - uk.companieshouse:12345678
   - uk.electoralcommission:EC123456
   - uk.publicwhip:uk.org.publicwhip/person/12345

Level 2: Strong Alias Match (Confidence: 0.95 - Auto-merge with review flag)
   - Exact match on OtherName.name where OtherName.alias_type = 'strong'
   - Case-insensitive, whitespace-normalized only
   - Example: "UNITE THE UNION" matches "Unite the Union"

Level 3: Normalized Name Match (Confidence: 0.80 - Human review required)
   - Conservative normalization (see below)
   - Only removes unambiguous legal suffixes
   - Example: "Quinn Estates Ltd." -> "quinn estates"

Level 4: Weak Alias Match (Confidence: 0.60 - Human review required)
   - Matches on OtherName.name where OtherName.alias_type = 'weak'
   - Aggressive normalization applied
   - Example: "Unite" as weak alias for "Unite the Union"

Level 5: Fuzzy Match (Confidence: 0.40 - Flag only, never auto-merge)
   - Levenshtein distance > 0.90 similarity
   - Phonetic matching (Metaphone/Soundex)
   - Create review task, never merge automatically
```

**Schema Changes for Weighted Aliases:**

```python
# datafetch/models/models.py

class OtherName(Dateframeable, GenericRelatable, models.Model):
    """
    An alternate or former name with confidence weighting.
    """
    ALIAS_TYPES = [
        ('strong', 'Strong Alias (exact variant)'),
        ('weak', 'Weak Alias (requires context)'),
        ('former', 'Former Name'),
        ('trading', 'Trading As'),
        ('abbreviated', 'Abbreviation'),
    ]

    name = models.CharField(_("name"), max_length=512)
    name_normalized = models.CharField(
        max_length=512,
        db_index=True,
        blank=True,
        help_text="Auto-populated normalized form for matching"
    )
    alias_type = models.CharField(
        max_length=20,
        choices=ALIAS_TYPES,
        default='strong',
        db_index=True
    )
    note = models.CharField(_("note"), max_length=1024, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['name_normalized', 'alias_type']),
        ]


class Actor(PolymorphicModel, ...):
    name = models.CharField(max_length=512, ...)
    name_normalized = models.CharField(max_length=512, db_index=True, blank=True)

    # Canonical actor for merged duplicates
    canonical_actor = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='aliases_of'
    )
    is_canonical = models.BooleanField(default=True, db_index=True)

    # Match confidence when this actor was created via resolution
    resolution_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence score from entity resolution (0.0-1.0)"
    )
    resolution_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Method used to resolve this entity (identifier, strong_alias, etc.)"
    )
```

**Conservative vs Aggressive Normalization:**

```python
# datafetch/resolution/normalization.py

import re
import unicodedata
from typing import Tuple

# Only remove suffixes that NEVER carry semantic meaning
CONSERVATIVE_SUFFIXES = [
    r'\blimited\b', r'\bltd\.?\b', r'\bplc\b', r'\bllp\b',
    r'\binc\.?\b', r'\bincorporated\b', r'\bcorp\.?\b', r'\bcorporation\b',
]

# Aggressive suffixes - may carry meaning, use only for weak matching
AGGRESSIVE_SUFFIXES = CONSERVATIVE_SUFFIXES + [
    r'\bthe\b', r'\bunion\b', r'\btrade union\b',
    r'\bgroup\b', r'\bholdings\b', r'\buk\b',
]


def normalize_conservative(name: str) -> str:
    """
    Conservative normalization for Level 3 matching.
    Only removes unambiguous legal suffixes.

    "Quinn Estates Ltd." -> "quinn estates"
    "Unite the Union" -> "unite the union"  # 'union' preserved
    """
    if not name:
        return ''

    # Normalize unicode
    name = unicodedata.normalize('NFKD', name)
    name = name.lower()

    # Remove punctuation except hyphens
    name = re.sub(r'[^\w\s-]', '', name)

    # Remove only conservative suffixes
    for pattern in CONSERVATIVE_SUFFIXES:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    return ' '.join(name.split()).strip()


def normalize_aggressive(name: str) -> str:
    """
    Aggressive normalization for Level 4 weak alias matching.
    Use with caution - higher false positive risk.

    "Unite the Union" -> "unite"
    "The Labour Party" -> "labour party"
    """
    if not name:
        return ''

    name = unicodedata.normalize('NFKD', name)
    name = name.lower()
    name = re.sub(r'[^\w\s-]', '', name)

    for pattern in AGGRESSIVE_SUFFIXES:
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    return ' '.join(name.split()).strip()


def compute_match_confidence(
    name1: str,
    name2: str,
    match_type: str
) -> Tuple[float, str]:
    """
    Compute confidence score for a potential match.

    Returns:
        Tuple of (confidence_score, explanation)
    """
    if match_type == 'identifier':
        return (1.0, "Exact identifier match")

    norm1_conservative = normalize_conservative(name1)
    norm2_conservative = normalize_conservative(name2)

    # Exact match after conservative normalization
    if norm1_conservative == norm2_conservative:
        return (0.85, f"Conservative normalization match: '{norm1_conservative}'")

    norm1_aggressive = normalize_aggressive(name1)
    norm2_aggressive = normalize_aggressive(name2)

    # Match only after aggressive normalization - lower confidence
    if norm1_aggressive == norm2_aggressive:
        return (0.60, f"Aggressive normalization match: '{norm1_aggressive}' (review recommended)")

    # Fuzzy matching
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, norm1_conservative, norm2_conservative).ratio()

    if ratio > 0.90:
        return (ratio * 0.5, f"Fuzzy match ({ratio:.0%} similar) - human review required")

    return (0.0, "No match")
```

**Trade-off Analysis:**

| Approach | Pros | Cons |
|----------|------|------|
| Original (aggressive) | Simple, fewer duplicates | False positives ("Unite" matches unrelated) |
| Weighted (recommended) | Precision, audit trail | More complex, requires alias curation |

**Implementation Priority:** Phase 3.1 (Weeks 1-2)

#### 1.2.2 Non-Destructive Merge Strategy

**Critique Addressed:** The original recommendation to update `donor_id` foreign keys when merging duplicates is destructive and loses the audit trail of how data was originally imported. The solution is to add `canonical_donor_id` fields that preserve the original import state.

**Design Principle:** Never modify the original import data. Instead, add a canonical reference layer that can be recomputed or reversed.

**Schema Changes for Non-Destructive Merges:**

```python
# datafetch/models/influence_mapping.py

class Donation(Relationship):
    # Original import fields (NEVER modify after import)
    donor = models.ForeignKey(
        'Actor',
        related_name='donated_to',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original donor as imported from source"
    )
    recipient = models.ForeignKey(
        'Actor',
        related_name='received_donations_from',
        null=True,
        on_delete=models.SET_NULL,
        help_text="Original recipient as imported from source"
    )

    # Canonical reference fields (updated by entity resolution)
    canonical_donor = models.ForeignKey(
        'Actor',
        related_name='canonical_donations_made',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical donor after entity resolution"
    )
    canonical_recipient = models.ForeignKey(
        'Actor',
        related_name='canonical_donations_received',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        help_text="Resolved canonical recipient after entity resolution"
    )

    # Resolution metadata
    donor_resolution_confidence = models.FloatField(
        null=True,
        blank=True,
        help_text="Confidence of donor resolution (1.0 = same as original)"
    )
    recipient_resolution_confidence = models.FloatField(
        null=True,
        blank=True
    )
    resolution_date = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When entity resolution was last applied"
    )

    @property
    def effective_donor(self) -> 'Actor':
        """Returns canonical donor if resolved, otherwise original."""
        return self.canonical_donor or self.donor

    @property
    def effective_recipient(self) -> 'Actor':
        """Returns canonical recipient if resolved, otherwise original."""
        return self.canonical_recipient or self.recipient

    class Meta:
        indexes = [
            models.Index(fields=['canonical_donor']),
            models.Index(fields=['canonical_recipient']),
            models.Index(fields=['donor', 'canonical_donor']),  # For resolution audits
        ]


class Consultancy(Relationship):
    # Same pattern as Donation
    client = models.ForeignKey('Actor', related_name='consulting_agencies', null=True, on_delete=models.SET_NULL)
    agency = models.ForeignKey('Actor', related_name='consulting_clients', null=True, on_delete=models.SET_NULL)

    canonical_client = models.ForeignKey(
        'Actor',
        related_name='canonical_consultancy_clients',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
    canonical_agency = models.ForeignKey(
        'Actor',
        related_name='canonical_consultancy_agencies',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )
```

**Entity Resolution Merge Function:**

```python
# datafetch/resolution/merges.py

from datetime import datetime
from typing import List, Optional
from django.db import transaction
from django.contrib.contenttypes.models import ContentType

from datafetch.models import Actor, Donation, Consultancy, Identifier, OtherName, Note


class MergeAuditLog(models.Model):
    """Audit trail for all entity merges - enables reversal."""
    canonical_actor = models.ForeignKey(Actor, on_delete=models.CASCADE, related_name='merge_logs')
    merged_actor_id = models.IntegerField(help_text="Original ID of merged actor")
    merged_actor_name = models.CharField(max_length=512)
    merge_reason = models.CharField(max_length=100)
    confidence = models.FloatField()
    merged_by = models.CharField(max_length=100, blank=True)  # User or 'system'
    merged_at = models.DateTimeField(auto_now_add=True)
    is_reversed = models.BooleanField(default=False)
    reversed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['merged_actor_id']),
            models.Index(fields=['canonical_actor', 'is_reversed']),
        ]


@transaction.atomic
def merge_actors_non_destructive(
    canonical: Actor,
    duplicates: List[Actor],
    confidence: float,
    reason: str,
    merged_by: str = 'system'
) -> List[MergeAuditLog]:
    """
    Merge duplicate actors into canonical actor WITHOUT modifying original FKs.

    This function:
    1. Updates canonical_* fields on Donation/Consultancy
    2. Copies identifiers and aliases to canonical
    3. Marks duplicates as non-canonical
    4. Creates audit log for potential reversal

    Args:
        canonical: The actor to merge INTO
        duplicates: List of actors to merge FROM
        confidence: Resolution confidence (0.0-1.0)
        reason: Why these were merged (e.g., 'identifier_match')
        merged_by: User or 'system'

    Returns:
        List of MergeAuditLog entries created
    """
    audit_logs = []
    now = datetime.now()

    for dup in duplicates:
        if dup.id == canonical.id:
            continue

        # 1. Update canonical references on Donations (preserve original donor_id)
        Donation.objects.filter(donor=dup).update(
            canonical_donor=canonical,
            donor_resolution_confidence=confidence,
            resolution_date=now
        )
        Donation.objects.filter(recipient=dup).update(
            canonical_recipient=canonical,
            recipient_resolution_confidence=confidence,
            resolution_date=now
        )

        # 2. Update canonical references on Consultancies
        Consultancy.objects.filter(client=dup).update(
            canonical_client=canonical
        )
        Consultancy.objects.filter(agency=dup).update(
            canonical_agency=canonical
        )

        # 3. Copy identifiers to canonical (avoid duplicates)
        for ident in dup.identifiers.all():
            Identifier.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(canonical),
                object_id=canonical.id,
                scheme=ident.scheme,
                identifier=ident.identifier
            )

        # 4. Add original name as strong alias
        OtherName.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(canonical),
            object_id=canonical.id,
            name=dup.name,
            defaults={
                'alias_type': 'strong',
                'note': f'Merged from Actor #{dup.id} on {now.date()}'
            }
        )

        # 5. Mark duplicate as non-canonical
        dup.canonical_actor = canonical
        dup.is_canonical = False
        dup.save(update_fields=['canonical_actor', 'is_canonical'])

        # 6. Create audit log
        log = MergeAuditLog.objects.create(
            canonical_actor=canonical,
            merged_actor_id=dup.id,
            merged_actor_name=dup.name,
            merge_reason=reason,
            confidence=confidence,
            merged_by=merged_by
        )
        audit_logs.append(log)

        # 7. Add note to canonical for visibility
        Note.objects.create(
            content_type=ContentType.objects.get_for_model(canonical),
            object_id=canonical.id,
            content=f'MERGE: Absorbed "{dup.name}" (ID: {dup.id}) - {reason} (confidence: {confidence:.0%})'
        )

    return audit_logs


@transaction.atomic
def reverse_merge(audit_log: MergeAuditLog) -> bool:
    """
    Reverse a previous merge operation.

    Returns True if successful, False if already reversed.
    """
    if audit_log.is_reversed:
        return False

    # Find the original duplicate actor
    try:
        dup = Actor.objects.get(id=audit_log.merged_actor_id)
    except Actor.DoesNotExist:
        # Actor was hard-deleted, cannot reverse
        return False

    # 1. Clear canonical references that point to this merge
    Donation.objects.filter(
        canonical_donor=audit_log.canonical_actor,
        donor=dup
    ).update(
        canonical_donor=None,
        donor_resolution_confidence=None,
        resolution_date=None
    )
    Donation.objects.filter(
        canonical_recipient=audit_log.canonical_actor,
        recipient=dup
    ).update(
        canonical_recipient=None,
        recipient_resolution_confidence=None,
        resolution_date=None
    )

    Consultancy.objects.filter(
        canonical_client=audit_log.canonical_actor,
        client=dup
    ).update(canonical_client=None)
    Consultancy.objects.filter(
        canonical_agency=audit_log.canonical_actor,
        agency=dup
    ).update(canonical_agency=None)

    # 2. Restore duplicate as canonical
    dup.canonical_actor = None
    dup.is_canonical = True
    dup.save(update_fields=['canonical_actor', 'is_canonical'])

    # 3. Mark audit log as reversed
    audit_log.is_reversed = True
    audit_log.reversed_at = datetime.now()
    audit_log.save()

    return True
```

**Migration Strategy for Existing Data:**

```python
# datafetch/migrations/XXXX_add_canonical_fields.py

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('datafetch', 'previous_migration'),
    ]

    operations = [
        # 1. Add canonical fields to Donation
        migrations.AddField(
            model_name='donation',
            name='canonical_donor',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='canonical_donations_made',
                to='datafetch.actor',
            ),
        ),
        migrations.AddField(
            model_name='donation',
            name='canonical_recipient',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='canonical_donations_received',
                to='datafetch.actor',
            ),
        ),
        migrations.AddField(
            model_name='donation',
            name='donor_resolution_confidence',
            field=models.FloatField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='donation',
            name='resolution_date',
            field=models.DateTimeField(blank=True, null=True),
        ),

        # 2. Add indexes for efficient queries
        migrations.AddIndex(
            model_name='donation',
            index=models.Index(fields=['canonical_donor'], name='idx_donation_canonical_donor'),
        ),
        migrations.AddIndex(
            model_name='donation',
            index=models.Index(fields=['canonical_recipient'], name='idx_donation_canonical_recip'),
        ),

        # 3. Same for Consultancy
        migrations.AddField(
            model_name='consultancy',
            name='canonical_client',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='canonical_consultancy_clients',
                to='datafetch.actor',
            ),
        ),
        migrations.AddField(
            model_name='consultancy',
            name='canonical_agency',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.SET_NULL,
                related_name='canonical_consultancy_agencies',
                to='datafetch.actor',
            ),
        ),
    ]


# Data migration to initialize canonical fields
def initialize_canonical_fields(apps, schema_editor):
    """
    For unmerged actors, canonical_* = original (confidence 1.0).
    This makes queries consistent before any merges occur.
    """
    Donation = apps.get_model('datafetch', 'Donation')

    # Batch update for performance
    Donation.objects.filter(
        canonical_donor__isnull=True,
        donor__isnull=False
    ).update(
        canonical_donor=models.F('donor'),
        donor_resolution_confidence=1.0
    )
    Donation.objects.filter(
        canonical_recipient__isnull=True,
        recipient__isnull=False
    ).update(
        canonical_recipient=models.F('recipient'),
        recipient_resolution_confidence=1.0
    )
```

**Query Patterns After Migration:**

```python
# BEFORE: Queries use donor_id directly (loses merged actors)
Donation.objects.filter(donor_id=123)

# AFTER: Queries use effective_donor property or canonical_donor
# Option 1: Use canonical_donor (includes all merged aliases)
Donation.objects.filter(canonical_donor_id=123)

# Option 2: QuerySet method for clarity
class DonationQuerySet(models.QuerySet):
    def for_canonical_donor(self, actor_id: int):
        """Get all donations where canonical donor matches."""
        return self.filter(canonical_donor_id=actor_id)

    def for_original_donor(self, actor_id: int):
        """Get donations as originally imported (audit use)."""
        return self.filter(donor_id=actor_id)

# Aggregate endpoint uses canonical
def get_donor_totals(actor_id: int) -> dict:
    return Donation.objects.filter(
        canonical_donor_id=actor_id
    ).aggregate(
        total=Sum('value'),
        count=Count('id')
    )
```

**Trade-off Analysis:**

| Approach | Pros | Cons |
|----------|------|------|
| Destructive (update FKs) | Simple queries, smaller indexes | Loses audit trail, irreversible |
| Non-destructive (recommended) | Full audit trail, reversible merges | Larger tables, more complex queries |

**Implementation Priority:** Phase 3.1 (Week 2-3)

### 1.3 Party Affiliation Architecture (Priority 2)

**Updated Understanding:**

The database contains 1.85 BILLION in donations to entities classified as "Political Party" (using the correct classification value). The challenge is not missing data but rather:
1. Aggregating individual MP donations by their party affiliation at the time of donation
2. Handling MPs who switch parties (e.g., Labour in 2010, Independent in 2024)
3. Efficiently querying historical party affiliation without expensive joins

**Current State:**
```
Person -> Membership -> Organization (with classification='Political Party')
```

The `on_behalf_of` field on Membership already contains party affiliation, but temporal queries are expensive.

**Recommended Schema Enhancement:**

```python
class Person(Actor):
    # Existing fields...

    # Denormalized current party for efficient queries
    current_party = models.ForeignKey(
        'Organization',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='current_members',
        help_text="Denormalized current party affiliation for query efficiency"
    )

class PartyMembership(Dateframeable, Timestampable, models.Model):
    """
    Explicit party affiliation history.
    Distinct from general Membership to enable party-specific temporal queries.
    Critical for "which party was this MP in when they received this donation?"
    """
    person = models.ForeignKey(
        'Person',
        related_name='party_history',
        on_delete=models.CASCADE
    )
    party = models.ForeignKey(
        'Organization',
        limit_choices_to={'classification': 'Political Party'},
        related_name='member_history',
        on_delete=models.CASCADE
    )

    class Meta:
        ordering = ['-start_date']
        indexes = [
            # Critical for temporal party lookups
            models.Index(fields=['person', 'start_date', 'end_date']),
            models.Index(fields=['party', 'start_date']),
        ]
```

**Population Strategy:**

```python
def infer_party_from_memberships():
    """
    Populate party affiliations from existing Membership data.
    ParlParse records include on_behalf_of for party affiliation.
    Note: Uses 'Political Party' which is the correct classification value.
    """
    from datafetch.models import Person, Membership, PartyMembership

    for person in Person.objects.filter(current_party__isnull=True):
        # Get all memberships with party affiliation, ordered by date
        memberships = person.memberships.filter(
            on_behalf_of__classification='Political Party'
        ).order_by('start_date')

        for membership in memberships:
            # Create PartyMembership record for each stint
            PartyMembership.objects.get_or_create(
                person=person,
                party=membership.on_behalf_of,
                start_date=membership.start_date,
                defaults={
                    'end_date': membership.end_date
                }
            )

        # Set current_party to the most recent
        latest = memberships.order_by('-start_date').first()
        if latest:
            person.current_party = latest.on_behalf_of
            person.save(update_fields=['current_party'])
```

#### 1.3.1 Temporal Party Affiliation Queries

**Critique Addressed:** The `current_party` denormalization does not account for historical influence. An MP who was Labour in 2010 but Independent in 2024 should have their 2010 donations attributed to Labour historically.

**Solution:** Provide temporal party lookup functions and API endpoints that accept `?at_date=` parameters.

**Temporal Lookup Function:**

```python
# datafetch/party_affiliation.py

from datetime import date
from typing import Optional
from django.db.models import Q

from datafetch.models import Person, Organization, PartyMembership


def get_party_at_date(person: Person, target_date: date) -> Optional[Organization]:
    """
    Get the party affiliation for a person at a specific date.

    Args:
        person: The Person to look up
        target_date: The date to check (usually donation received_date)

    Returns:
        Organization (party) or None if no affiliation found
    """
    membership = PartyMembership.objects.filter(
        person=person,
        start_date__lte=target_date
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=target_date)
    ).order_by('-start_date').first()

    return membership.party if membership else None


def get_party_at_date_bulk(person_ids: list[int], target_date: date) -> dict[int, int]:
    """
    Bulk lookup of party affiliations at a specific date.
    Optimized for aggregation queries.

    Returns:
        Dict mapping person_id to party_id
    """
    memberships = PartyMembership.objects.filter(
        person_id__in=person_ids,
        start_date__lte=target_date
    ).filter(
        Q(end_date__isnull=True) | Q(end_date__gte=target_date)
    ).values('person_id', 'party_id').order_by('person_id', '-start_date')

    # Take the most recent membership per person
    result = {}
    for m in memberships:
        if m['person_id'] not in result:
            result[m['person_id']] = m['party_id']

    return result
```

**SQL for Time-Bounded Party Aggregation:**

```sql
-- Aggregate donations by party affiliation at time of donation
-- This correctly attributes a 2010 donation to an MP's 2010 party,
-- even if they've since switched parties

WITH donation_with_party AS (
    SELECT
        d.id AS donation_id,
        d.value,
        d.received_date,
        d.recipient_id,
        p.id AS person_id,
        -- Get party affiliation at time of donation
        (
            SELECT pm.party_id
            FROM datafetch_partymembership pm
            WHERE pm.person_id = p.id
              AND pm.start_date <= d.received_date
              AND (pm.end_date IS NULL OR pm.end_date >= d.received_date)
            ORDER BY pm.start_date DESC
            LIMIT 1
        ) AS party_id_at_donation
    FROM datafetch_donation d
    JOIN datafetch_person p ON p.actor_ptr_id = d.recipient_id
    WHERE d.received_date BETWEEN '2010-01-01' AND '2024-12-31'
)
SELECT
    o.name AS party_name,
    o.id AS party_id,
    COUNT(*) AS donation_count,
    SUM(dwp.value) AS total_value,
    COUNT(DISTINCT dwp.person_id) AS mp_count
FROM donation_with_party dwp
JOIN datafetch_organization o ON o.actor_ptr_id = dwp.party_id_at_donation
GROUP BY o.id, o.name
ORDER BY total_value DESC;
```

**Materialized View for Performance:**

```sql
-- Pre-compute party affiliation snapshots for common date ranges
CREATE MATERIALIZED VIEW mv_donation_party_affiliation AS
SELECT
    d.id AS donation_id,
    d.donor_id,
    d.recipient_id,
    d.value,
    d.received_date,
    EXTRACT(YEAR FROM d.received_date) AS donation_year,
    -- Party at time of donation (for MP recipients)
    (
        SELECT pm.party_id
        FROM datafetch_partymembership pm
        WHERE pm.person_id = p.id
          AND pm.start_date <= d.received_date
          AND (pm.end_date IS NULL OR pm.end_date >= d.received_date)
        ORDER BY pm.start_date DESC
        LIMIT 1
    ) AS recipient_party_at_donation,
    -- Current party (for comparison)
    p.current_party_id AS recipient_current_party
FROM datafetch_donation d
LEFT JOIN datafetch_person p ON p.actor_ptr_id = d.recipient_id
WHERE d.value > 0;

CREATE INDEX idx_mv_donation_party_year ON mv_donation_party_affiliation (donation_year, recipient_party_at_donation);
CREATE INDEX idx_mv_donation_party ON mv_donation_party_affiliation (recipient_party_at_donation);

-- Refresh strategy: run after imports or daily
-- REFRESH MATERIALIZED VIEW CONCURRENTLY mv_donation_party_affiliation;
```

**Trade-off Analysis:**

| Approach | Pros | Cons |
|----------|------|------|
| current_party only | Simple queries, fast | Historically inaccurate |
| Runtime temporal lookup | Always accurate | Slow for aggregations |
| Materialized view (recommended) | Accurate + fast | Storage overhead, refresh needed |

**Implementation Priority:** Phase 3.2 (Weeks 4-5)

### 1.4 Organization Taxonomy (Priority 3)

**The Core Problem:**

The `classification` field is a free-text CharField containing inconsistent values:
- "Trade Union", "trade union", "Union"
- "Company", "Limited Company", "PLC"
- "Party", "Political Party"

This makes faceted filtering unreliable.

**Recommended Schema:**

```python
class OrganizationType(models.Model):
    """Controlled vocabulary for organization classification."""
    slug = models.SlugField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ['name']

# Initial data
ORGANIZATION_TYPES = [
    ('party', 'Political Party', None),
    ('trade-union', 'Trade Union', None),
    ('company', 'Company', None),
    ('company-plc', 'Public Limited Company', 'company'),
    ('company-ltd', 'Private Limited Company', 'company'),
    ('company-llp', 'Limited Liability Partnership', 'company'),
    ('lobby-agency', 'Lobbying Agency', 'company'),
    ('public-body', 'Public Body', None),
    ('charity', 'Charity', None),
    ('think-tank', 'Think Tank', None),
    ('campaign', 'Campaign Group', None),
    ('individual', 'Individual/Unincorporated', None),
]

class Organization(Actor):
    # Keep existing classification for backward compatibility
    classification = models.CharField(...)

    # Add typed classification
    organization_type = models.ForeignKey(
        OrganizationType,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='organizations'
    )
```

**Migration Mapping:**

```python
CLASSIFICATION_MAPPING = {
    'trade union': 'trade-union',
    'union': 'trade-union',
    'party': 'party',
    'political party': 'party',
    'company': 'company',
    'limited company': 'company-ltd',
    'public limited company': 'company-plc',
    'plc': 'company-plc',
    'limited': 'company-ltd',
    'ltd': 'company-ltd',
    'llp': 'company-llp',
    # etc.
}
```

### 1.5 Sector/Industry Classification (Priority 4)

**Use Case:** Enable queries like "donations from the property sector" or "pharmaceutical lobbying spend".

**Recommended Approach:**

This is lower priority because:
1. Requires significant manual curation (Companies House SIC codes are incomplete)
2. Industry boundaries are fuzzy (is Amazon "tech" or "retail"?)
3. Most value comes from entity-level analysis, not industry aggregates

**If Implemented:**

```python
class Sector(models.Model):
    """Industry sector classification."""
    slug = models.SlugField(primary_key=True, max_length=50)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

class Organization(Actor):
    sectors = models.ManyToManyField(Sector, blank=True, related_name='organizations')
```

**Recommended Phase 3 Scope:** Skip automated sector classification. Instead:
1. Allow manual tagging of top 200 donors/clients
2. Build UI for editorial staff to curate sector assignments
3. Do not expose sector filtering until data quality is high

---

## Part 2: API Design Strategy

### 2.1 Critique of Current API

**Current State:**

The existing API is CRUD-oriented with minimal filtering:

| Endpoint | Purpose | Limitation |
|----------|---------|------------|
| `/api/actors/` | List actors with `?search=` | No type filtering, no aggregation |
| `/api/politicians/` | List persons with memberships | Date filtering is broken (string comparison) |
| `/api/actors/{pk}/donations-from/` | Donations received | No value thresholds, no date ranges |
| `/api/actors/{pk}/donations-to/` | Donations made | Same limitations |

**Problems:**

1. **No aggregate endpoints:** Frontend must fetch all records and compute totals client-side
2. **No standardized filtering:** Each endpoint implements filtering differently
3. **No versioning:** Breaking changes cannot be deployed safely
4. **No pagination metadata:** Just count/next/previous, no total pages
5. **No HATEOAS compliance:** Related resources require URL construction

### 2.2 API Design Principles for Phase 3

**Principle 1: Analysis-First Endpoints**

The primary consumers are visualizations and data cards, not CRUD interfaces. Design endpoints for common queries, not generic resources.

**Principle 2: Pre-Computed Aggregates**

With 119,599 donations, real-time aggregation is expensive. Use database views or cached aggregates for leaderboards.

**Principle 3: Universal Filter Schema**

Every data endpoint should accept the same filter parameters for consistency:

```
?date_from=2020-01-01
?date_to=2024-12-31
?min_value=10000
?donor_type=organization|individual
?recipient_type=person|party|organization
?has_lobbying=true
```

**Principle 4: Temporal Query Parameters**

For endpoints that involve party affiliation, support temporal queries:

```
?at_date=2010-01-01          # Single point-in-time query
?from_date=2010-01-01        # Range start (party affiliation at each donation date)
?to_date=2024-12-31          # Range end
?use_historical_party=true   # Use party at donation time vs current party
```

**Principle 5: Explicit Versioning**

```
/api/v2/aggregates/top-donors/
/api/v2/actors/{pk}/summary/
```

### 2.2.1 Temporal Party Aggregation Endpoint

**Critique Addressed:** The API must support historical party affiliation queries where donations are attributed to the party the MP belonged to at the time of the donation.

**Endpoint Design:**

```yaml
# Party donations with temporal affiliation
GET /api/v2/aggregates/party-donations/
Parameters:
  - at_date: YYYY-MM-DD (optional, for point-in-time snapshot)
  - from_date: YYYY-MM-DD (default: all time)
  - to_date: YYYY-MM-DD (default: today)
  - use_historical_party: boolean (default: true)
  - include_direct: boolean (include donations directly to parties, default: true)
  - include_mps: boolean (include donations to MPs attributed to party, default: true)

Response:
  meta:
    from_date: "2010-01-01"
    to_date: "2024-12-31"
    use_historical_party: true
  parties:
    - party_id: 123
      party_name: "Labour Party"
      direct_donations:
        total: 456000000
        count: 2341
      mp_donations:
        total: 12500000
        count: 8234
        mp_count: 312
      combined_total: 468500000
    - party_id: 456
      party_name: "Conservative Party"
      ...

# Example: What did Labour MPs receive while they were Labour MPs (2010-2015)?
GET /api/v2/aggregates/party-donations/?from_date=2010-01-01&to_date=2015-05-07&use_historical_party=true
```

**Implementation:**

```python
# api/views/party_aggregates.py

from datetime import date
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db.models import Sum, Count, Q, F
from django.db.models.functions import Coalesce

from datafetch.models import Donation, Organization, Person


class PartyDonationsView(APIView):
    """
    Aggregate donations by party with temporal affiliation support.
    """

    def get(self, request):
        # Parse parameters
        from_date = request.query_params.get('from_date')
        to_date = request.query_params.get('to_date')
        at_date = request.query_params.get('at_date')
        use_historical = request.query_params.get('use_historical_party', 'true').lower() == 'true'
        include_direct = request.query_params.get('include_direct', 'true').lower() == 'true'
        include_mps = request.query_params.get('include_mps', 'true').lower() == 'true'

        # Use point-in-time if specified
        if at_date:
            from_date = at_date
            to_date = at_date

        # Get all parties
        parties = Organization.objects.filter(
            classification='Political Party'
        ).values('id', 'name')

        results = []

        for party in parties:
            party_data = {
                'party_id': party['id'],
                'party_name': party['name'],
            }

            # Direct donations to the party itself
            if include_direct:
                direct_qs = Donation.objects.filter(
                    recipient_id=party['id']
                )
                if from_date:
                    direct_qs = direct_qs.filter(received_date__gte=from_date)
                if to_date:
                    direct_qs = direct_qs.filter(received_date__lte=to_date)

                direct_agg = direct_qs.aggregate(
                    total=Coalesce(Sum('value'), 0),
                    count=Count('id')
                )
                party_data['direct_donations'] = direct_agg

            # Donations to MPs affiliated with this party
            if include_mps:
                if use_historical:
                    # Use materialized view for historical accuracy
                    mp_agg = self._get_historical_mp_donations(
                        party['id'], from_date, to_date
                    )
                else:
                    # Use current party (faster but less accurate)
                    mp_agg = self._get_current_mp_donations(
                        party['id'], from_date, to_date
                    )
                party_data['mp_donations'] = mp_agg

            # Combined total
            direct_total = party_data.get('direct_donations', {}).get('total', 0)
            mp_total = party_data.get('mp_donations', {}).get('total', 0)
            party_data['combined_total'] = direct_total + mp_total

            results.append(party_data)

        # Sort by combined total
        results.sort(key=lambda x: x['combined_total'], reverse=True)

        return Response({
            'meta': {
                'from_date': from_date,
                'to_date': to_date,
                'use_historical_party': use_historical,
            },
            'parties': results
        })

    def _get_historical_mp_donations(self, party_id: int, from_date, to_date) -> dict:
        """Use materialized view for historically accurate party attribution."""
        from django.db import connection

        sql = """
            SELECT
                COUNT(*) AS count,
                COALESCE(SUM(value), 0) AS total,
                COUNT(DISTINCT recipient_id) AS mp_count
            FROM mv_donation_party_affiliation
            WHERE recipient_party_at_donation = %s
        """
        params = [party_id]

        if from_date:
            sql += " AND received_date >= %s"
            params.append(from_date)
        if to_date:
            sql += " AND received_date <= %s"
            params.append(to_date)

        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()

        return {
            'count': row[0],
            'total': float(row[1]),
            'mp_count': row[2]
        }

    def _get_current_mp_donations(self, party_id: int, from_date, to_date) -> dict:
        """Use current_party for faster but less accurate attribution."""
        mp_ids = Person.objects.filter(
            current_party_id=party_id
        ).values_list('id', flat=True)

        qs = Donation.objects.filter(recipient_id__in=mp_ids)
        if from_date:
            qs = qs.filter(received_date__gte=from_date)
        if to_date:
            qs = qs.filter(received_date__lte=to_date)

        return qs.aggregate(
            total=Coalesce(Sum('value'), 0),
            count=Count('id'),
            mp_count=Count('recipient_id', distinct=True)
        )
```

**URL Configuration:**

```python
# api/urls.py

from django.urls import path
from api.views.party_aggregates import PartyDonationsView

urlpatterns = [
    # ... existing patterns ...
    path('v2/aggregates/party-donations/', PartyDonationsView.as_view(), name='party-donations'),
]
```

### 2.3 Recommended Endpoint Architecture

**Tier 1: Aggregate Endpoints (Build First)**

These power the key visualizations and require database optimization:

```yaml
# Power Concentration (Pareto visualization)
GET /api/v2/aggregates/concentration/
Parameters:
  - bracket_type: donation_value | donor_total
  - date_from, date_to
Response:
  brackets:
    - label: "1M+"
      donor_count: 277
      total_value: 1361600000
      pct_of_total: 65.09
    - label: "500K-1M"
      ...

# Top Donors Leaderboard
GET /api/v2/aggregates/top-donors/
Parameters:
  - limit: 20 (default)
  - donor_type: all | organization | individual
  - recipient_type: all | person | party
  - date_from, date_to
  - min_value
Response:
  results:
    - donor_id: 123
      donor_name: "Unite the Union"
      donor_type: "Trade Union"
      total_donated: 67200000
      donation_count: 1138
      distinct_recipients: 115
      latest_donation: "2024-11-15"

# Lobbying-Donation Overlap
GET /api/v2/aggregates/overlap/
Parameters:
  - date_from, date_to
Response:
  summary:
    overlap_count: 61
    total_donated_by_lobbying_clients: 98500000
    distinct_recipients: 234
  top_overlaps:
    - org_id: 456
      org_name: "Unite the Union"
      consultancy_count: 4
      agencies_used: 3
      total_donated: 67200000

# Donation Flow Matrix
GET /api/v2/aggregates/flow-matrix/
Parameters:
  - date_from, date_to
Response:
  flows:
    - from_type: "Organization"
      to_type: "Individual"
      donation_count: 45000
      total_value: 890000000
      pct_of_total: 42.5
```

**Tier 2: Entity Summary Endpoints (Build Second)**

These power data cards and profile pages:

```yaml
# Actor Summary (for Data Cards)
GET /api/v2/actors/{pk}/summary/
Response:
  id: 123
  name: "Unite the Union"
  type: "Organization"
  classification: "Trade Union"
  image_url: "..."
  stats:
    total_donated: 67200000
    donation_count: 1138
    distinct_recipients: 115
    is_lobbying_client: true
    consultancy_count: 4
    first_donation: "2001-03-15"
    latest_donation: "2024-11-15"
  top_recipients:
    - id: 789
      name: "Labour Party"
      total: 45000000
    - id: 790
      name: "John Smith MP"
      total: 250000

# Actor Relationships
GET /api/v2/actors/{pk}/relationships/
Parameters:
  - relationship_type: donations_made | donations_received | consultancies
  - date_from, date_to
  - min_value
  - limit, offset
Response:
  donations_made:
    total: 67200000
    count: 1138
    items:
      - recipient_id: 789
        recipient_name: "Labour Party"
        value: 500000
        date: "2024-06-15"
        type: "Cash"
```

**Tier 3: Search Endpoint (Build Third)**

Unified search across actors and editorial content:

```yaml
GET /api/v2/search/
Parameters:
  - q: search query
  - type: actor | person | organization | page | all
  - limit, offset
Response:
  total: 145
  results:
    - type: "Person"
      id: 123
      name: "David Sainsbury"
      snippet: "Major donor to Labour Party..."
      relevance: 0.95
    - type: "Organization"
      id: 456
      name: "Sainsbury's Supermarkets Ltd"
      snippet: "..."
      relevance: 0.78
```

### 2.4 Database Optimization Strategy

**Indexes Required:**

```sql
-- Actor queries
CREATE INDEX idx_actor_name_normalized ON datafetch_actor (name_normalized);
CREATE INDEX idx_actor_is_canonical ON datafetch_actor (is_canonical) WHERE is_canonical = true;

-- Donation queries
CREATE INDEX idx_donation_donor ON datafetch_donation (donor_id);
CREATE INDEX idx_donation_recipient ON datafetch_donation (recipient_id);
CREATE INDEX idx_donation_received_date ON datafetch_donation (received_date);
CREATE INDEX idx_donation_value ON datafetch_donation (value) WHERE value > 0;

-- Composite indexes for common queries
CREATE INDEX idx_donation_donor_recipient ON datafetch_donation (donor_id, recipient_id);
CREATE INDEX idx_donation_recipient_date ON datafetch_donation (recipient_id, received_date DESC);

-- Organization type queries
CREATE INDEX idx_org_classification ON datafetch_organization (classification);
CREATE INDEX idx_org_type ON datafetch_organization (organization_type_id);

-- Membership queries for party affiliation
CREATE INDEX idx_membership_person_party ON datafetch_membership (person_id, on_behalf_of_id);
```

**Materialized Views for Aggregates:**

```sql
-- Donor totals (refresh daily or on import)
CREATE MATERIALIZED VIEW mv_donor_totals AS
SELECT
    donor_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_donated,
    COUNT(DISTINCT recipient_id) AS distinct_recipients,
    MIN(received_date) AS first_donation,
    MAX(received_date) AS latest_donation
FROM datafetch_donation
WHERE donor_id IS NOT NULL AND value > 0
GROUP BY donor_id;

CREATE UNIQUE INDEX idx_mv_donor_totals_pk ON mv_donor_totals (donor_id);

-- Recipient totals
CREATE MATERIALIZED VIEW mv_recipient_totals AS
SELECT
    recipient_id,
    COUNT(*) AS donation_count,
    SUM(value) AS total_received,
    COUNT(DISTINCT donor_id) AS distinct_donors,
    MIN(received_date) AS first_donation,
    MAX(received_date) AS latest_donation
FROM datafetch_donation
WHERE recipient_id IS NOT NULL AND value > 0
GROUP BY recipient_id;

-- Lobbying overlap summary
CREATE MATERIALIZED VIEW mv_lobbying_donors AS
SELECT
    c.client_id AS org_id,
    COUNT(DISTINCT c.agency_id) AS agencies_used,
    COUNT(c.id) AS consultancy_count,
    COALESCE(d.total_donated, 0) AS total_donated,
    COALESCE(d.donation_count, 0) AS donation_count,
    COALESCE(d.distinct_recipients, 0) AS distinct_recipients
FROM datafetch_consultancy c
LEFT JOIN mv_donor_totals d ON d.donor_id = c.client_id
GROUP BY c.client_id, d.total_donated, d.donation_count, d.distinct_recipients;
```

**Refresh Strategy:**

```python
from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Refresh materialized views for aggregate endpoints'

    def handle(self, *args, **options):
        views = [
            'mv_donor_totals',
            'mv_recipient_totals',
            'mv_lobbying_donors',
        ]

        with connection.cursor() as cursor:
            for view in views:
                self.stdout.write(f'Refreshing {view}...')
                cursor.execute(f'REFRESH MATERIALIZED VIEW CONCURRENTLY {view}')

        self.stdout.write(self.style.SUCCESS('All views refreshed'))
```

### 2.5 API Implementation with django-filter

```python
# api/filters.py
import django_filters
from datafetch.models import Donation, Actor, Organization

class DonationFilter(django_filters.FilterSet):
    date_from = django_filters.DateFilter(
        field_name='received_date',
        lookup_expr='gte'
    )
    date_to = django_filters.DateFilter(
        field_name='received_date',
        lookup_expr='lte'
    )
    min_value = django_filters.NumberFilter(
        field_name='value',
        lookup_expr='gte'
    )
    max_value = django_filters.NumberFilter(
        field_name='value',
        lookup_expr='lte'
    )
    donor_type = django_filters.ChoiceFilter(
        method='filter_donor_type',
        choices=[
            ('organization', 'Organization'),
            ('individual', 'Individual'),
        ]
    )
    has_lobbying = django_filters.BooleanFilter(
        method='filter_has_lobbying'
    )

    class Meta:
        model = Donation
        fields = ['donation_type', 'nature_of_donation']

    def filter_donor_type(self, queryset, name, value):
        if value == 'organization':
            return queryset.filter(donor__organization__isnull=False)
        elif value == 'individual':
            return queryset.filter(donor__person__isnull=False)
        return queryset

    def filter_has_lobbying(self, queryset, name, value):
        from datafetch.models import Consultancy
        lobbying_clients = Consultancy.objects.values_list('client_id', flat=True)
        if value:
            return queryset.filter(donor_id__in=lobbying_clients)
        return queryset.exclude(donor_id__in=lobbying_clients)
```

### 2.6 Caching Strategy

**Cache Levels:**

1. **Database-Level:** Materialized views (refresh on import, ~daily)
2. **Application-Level:** Redis cache for aggregate endpoints (TTL: 1 hour)
3. **HTTP-Level:** Cache-Control headers for static aggregates

**Implementation:**

```python
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from rest_framework.decorators import api_view
from rest_framework.response import Response

AGGREGATE_CACHE_TTL = 60 * 60  # 1 hour

@api_view(['GET'])
@cache_page(AGGREGATE_CACHE_TTL)
def top_donors(request):
    """Cached leaderboard endpoint."""
    cache_key = f"top_donors:{request.query_params.urlencode()}"
    result = cache.get(cache_key)

    if result is None:
        # Expensive query
        result = compute_top_donors(request.query_params)
        cache.set(cache_key, result, AGGREGATE_CACHE_TTL)

    return Response(result)
```

---

## Part 3: Data Layer Recommendations

### 3.1 Data Quality Issues to Address

**Priority 1: NULL Donor IDs**

The data analysis revealed donations with NULL `donor_id`. Investigation needed:

```sql
-- Identify sources of NULL donors
SELECT donation_type, COUNT(*)
FROM datafetch_donation
WHERE donor_id IS NULL
GROUP BY donation_type;
```

If these are from Lords' Register (free-text donor descriptions), consider:
1. Adding a `donor_text` field for unstructured donor info
2. Marking these explicitly as "unresolved"

**Priority 2: Date Format Inconsistency**

Some dates stored in CharField fail the YYYY-MM-DD regex. Clean up:

```sql
-- Find malformed dates
SELECT id, received_date
FROM datafetch_donation
WHERE received_date::text !~ '^\d{4}-\d{2}-\d{2}$'
  AND received_date IS NOT NULL;
```

**Priority 3: Organization Classification Normalization**

Run classification cleanup migration before adding OrganizationType FK.

### 3.2 Import Command Refactoring

**Current Problems:**

1. Each importer implements its own entity resolution
2. String matching is case-sensitive and exact
3. No audit trail for entity merges
4. Inconsistent error handling

**Recommended Shared Helper:**

```python
# datafetch/resolution.py

from typing import Optional, Dict, Any, List
from datafetch.models import Actor, Organization, Person, Identifier, OtherName

class ActorResolutionService:
    """
    Centralized entity resolution for all import commands.

    Resolution hierarchy:
    1. Identifier match (strongest)
    2. Normalized name match
    3. Alias match
    4. Create new (if no match)
    """

    def resolve_organization(
        self,
        name: str,
        identifiers: Optional[Dict[str, str]] = None,
        classification: Optional[str] = None,
        create_if_missing: bool = True
    ) -> Optional[Organization]:
        """
        Resolve an organization by name and/or identifiers.

        Args:
            name: Organization name (will be normalized)
            identifiers: Dict of {scheme: identifier} pairs
            classification: Organization type hint
            create_if_missing: Whether to create if not found

        Returns:
            Resolved or created Organization, or None
        """
        # 1. Try identifier match
        if identifiers:
            for scheme, identifier in identifiers.items():
                actor = self._find_by_identifier(scheme, identifier)
                if actor:
                    return self._ensure_organization(actor)

        # 2. Try normalized name match
        normalized = normalize_actor_name(name)
        actor = Actor.objects.filter(
            name_normalized=normalized,
            is_canonical=True
        ).first()
        if actor:
            return self._ensure_organization(actor)

        # 3. Try alias match
        alias = OtherName.objects.filter(
            name__iexact=normalized
        ).select_related('content_object').first()
        if alias and alias.content_object:
            return self._ensure_organization(alias.content_object)

        # 4. Create new
        if create_if_missing:
            org = Organization.objects.create(
                name=name,
                classification=classification or ''
            )

            # Add identifiers
            if identifiers:
                for scheme, identifier in identifiers.items():
                    Identifier.objects.create(
                        content_object=org,
                        scheme=scheme,
                        identifier=identifier
                    )

            return org

        return None

    def resolve_person(
        self,
        name: str,
        identifiers: Optional[Dict[str, str]] = None,
        create_if_missing: bool = True
    ) -> Optional[Person]:
        """Similar to resolve_organization but for Person entities."""
        # Implementation follows same pattern
        ...

    def _find_by_identifier(
        self,
        scheme: str,
        identifier: str
    ) -> Optional[Actor]:
        """Find actor by identifier scheme and value."""
        ident = Identifier.objects.filter(
            scheme=scheme,
            identifier=identifier
        ).first()
        if ident and ident.content_object:
            return ident.content_object
        return None

    def _ensure_organization(self, actor: Actor) -> Optional[Organization]:
        """Ensure actor is an Organization, return None if Person."""
        if isinstance(actor, Organization):
            return actor
        return None


# Usage in import commands:
resolver = ActorResolutionService()

org = resolver.resolve_organization(
    name="Quinn Estates Ltd",
    identifiers={'uk.companieshouse': '12345678'},
    classification='company'
)
```

### 3.3 Deduplication Strategy

**Phase 1: Automated Flagging**

```python
# management/commands/flag_duplicates.py

def flag_potential_duplicates():
    """
    Identify actors that may be duplicates based on normalized names.
    Does NOT merge - just flags for human review.
    """
    from django.db.models import Count

    # Find normalized names with multiple actors
    duplicates = Actor.objects.filter(
        is_canonical=True
    ).values(
        'name_normalized'
    ).annotate(
        count=Count('id')
    ).filter(
        count__gt=1
    )

    for dup in duplicates:
        actors = Actor.objects.filter(
            name_normalized=dup['name_normalized'],
            is_canonical=True
        )

        # Create review note
        for actor in actors:
            Note.objects.get_or_create(
                content_object=actor,
                content__startswith='DUPLICATE_REVIEW:',
                defaults={
                    'content': f'DUPLICATE_REVIEW: {actors.count()} actors share normalized name "{dup["name_normalized"]}"'
                }
            )
```

**Phase 2: Human Review Interface**

Build Django admin action or management command for merging:

```python
def merge_actors(canonical: Actor, duplicates: List[Actor]):
    """
    Merge duplicate actors into canonical actor.

    - Re-points all ForeignKeys to canonical
    - Copies identifiers and aliases to canonical
    - Marks duplicates as non-canonical
    """
    for dup in duplicates:
        if dup.id == canonical.id:
            continue

        # Re-point donations
        Donation.objects.filter(donor=dup).update(donor=canonical)
        Donation.objects.filter(recipient=dup).update(recipient=canonical)

        # Re-point consultancies
        Consultancy.objects.filter(client=dup).update(client=canonical)
        Consultancy.objects.filter(agency=dup).update(agency=canonical)

        # Copy identifiers
        for ident in dup.identifiers.all():
            Identifier.objects.get_or_create(
                content_type=ContentType.objects.get_for_model(canonical),
                object_id=canonical.id,
                scheme=ident.scheme,
                identifier=ident.identifier
            )

        # Add original name as alias
        OtherName.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(canonical),
            object_id=canonical.id,
            name=dup.name,
            defaults={'note': f'Merged from Actor #{dup.id}'}
        )

        # Mark as non-canonical
        dup.canonical_actor = canonical
        dup.is_canonical = False
        dup.save()

        # Create audit trail
        Note.objects.create(
            content_object=canonical,
            content=f'MERGE_AUDIT: Merged Actor #{dup.id} "{dup.name}" on {datetime.now()}'
        )
```

---

## Part 4: Implementation Priorities

### Phase 3.1: Foundation (Weeks 1-3)

**Must Have:**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| Add `name_normalized` field to Actor | 2 days | Critical | None |
| Implement normalization function | 1 day | Critical | None |
| Data migration for existing records | 1 day | Critical | Normalization function |
| Add database indexes | 1 day | High | None |
| Implement ActorResolutionService | 3 days | Critical | Normalization |
| Refactor import_ec to use resolver | 2 days | High | Resolution service |
| Refactor import_appc to use resolver | 2 days | High | Resolution service |

**Should Have:**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| Flag duplicate actors script | 1 day | High | name_normalized |
| Manual merge interface | 3 days | High | Flagging script |
| Add `current_party` to Person | 1 day | High | None |
| Party inference from memberships | 2 days | High | current_party field |

### Phase 3.2: API Layer (Weeks 4-6)

**Must Have:**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| Create materialized views | 2 days | Critical | Indexes |
| Implement /aggregates/top-donors/ | 2 days | Critical | MV |
| Implement /aggregates/concentration/ | 1 day | Critical | MV |
| Implement /aggregates/overlap/ | 2 days | High | MV |
| Implement /actors/{pk}/summary/ | 2 days | High | None |
| Add django-filter integration | 2 days | High | None |
| API versioning setup | 1 day | Medium | None |

**Should Have:**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| Redis caching for aggregates | 2 days | Medium | Aggregate endpoints |
| /aggregates/flow-matrix/ | 1 day | Medium | MV |
| Unified search endpoint | 3 days | Medium | Elasticsearch |

### Phase 3.3: Data Quality (Weeks 7-8)

**Should Have:**

| Task | Effort | Impact | Dependencies |
|------|--------|--------|--------------|
| OrganizationType model | 1 day | Medium | None |
| Classification mapping migration | 2 days | Medium | OrganizationType |
| PartyMembership model | 1 day | Medium | None |
| NULL donor investigation | 2 days | Medium | None |
| Date format cleanup | 1 day | Low | None |
| Materialized view refresh command | 1 day | Medium | MV |

### Deferred (Phase 4+)

- Sector classification model and UI
- Elasticsearch full deployment
- GraphQL API layer
- Real-time import webhooks
- Historical data versioning

---

## Appendix A: Model Changes Summary

```python
# Summary of all recommended model changes

# datafetch/models/models.py
class Actor(PolymorphicModel, ...):
    name_normalized = models.CharField(max_length=512, db_index=True, blank=True)
    canonical_actor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    is_canonical = models.BooleanField(default=True, db_index=True)

class Person(Actor):
    current_party = models.ForeignKey('Organization', null=True, blank=True, on_delete=models.SET_NULL)

class Organization(Actor):
    organization_type = models.ForeignKey('OrganizationType', null=True, blank=True, on_delete=models.SET_NULL)

# New models
class OrganizationType(models.Model):
    slug = models.SlugField(primary_key=True)
    name = models.CharField(max_length=100)
    parent = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

class PartyMembership(Dateframeable, Timestampable, models.Model):
    person = models.ForeignKey('Person', related_name='party_history', on_delete=models.CASCADE)
    party = models.ForeignKey('Organization', related_name='member_history', on_delete=models.CASCADE)
```

---

## Appendix B: SQL Optimization Summary

```sql
-- Required indexes
CREATE INDEX idx_actor_name_normalized ON datafetch_actor (name_normalized);
CREATE INDEX idx_actor_is_canonical ON datafetch_actor (is_canonical) WHERE is_canonical = true;
CREATE INDEX idx_donation_donor ON datafetch_donation (donor_id);
CREATE INDEX idx_donation_recipient ON datafetch_donation (recipient_id);
CREATE INDEX idx_donation_received_date ON datafetch_donation (received_date);
CREATE INDEX idx_donation_value ON datafetch_donation (value) WHERE value > 0;
CREATE INDEX idx_org_classification ON datafetch_organization (classification);
CREATE INDEX idx_membership_person_party ON datafetch_membership (person_id, on_behalf_of_id);

-- Required materialized views
CREATE MATERIALIZED VIEW mv_donor_totals AS ...;
CREATE MATERIALIZED VIEW mv_recipient_totals AS ...;
CREATE MATERIALIZED VIEW mv_lobbying_donors AS ...;
```

---

## Appendix C: API Endpoint Summary

| Endpoint | Method | Purpose | Priority |
|----------|--------|---------|----------|
| `/api/v2/aggregates/top-donors/` | GET | Leaderboard | P1 |
| `/api/v2/aggregates/concentration/` | GET | Pareto distribution | P1 |
| `/api/v2/aggregates/overlap/` | GET | Lobbying-donation intersection | P1 |
| `/api/v2/aggregates/party-donations/` | GET | Party totals with temporal affiliation | P1 |
| `/api/v2/aggregates/flow-matrix/` | GET | Donor-recipient type flows | P2 |
| `/api/v2/actors/{pk}/summary/` | GET | Entity card data | P1 |
| `/api/v2/actors/{pk}/relationships/` | GET | Filtered relationships | P2 |
| `/api/v2/search/` | GET | Unified search | P2 |

### Temporal Query Parameters (New)

All aggregate endpoints support these temporal parameters for historical party attribution:

| Parameter | Type | Description |
|-----------|------|-------------|
| `at_date` | YYYY-MM-DD | Point-in-time snapshot (overrides range) |
| `from_date` | YYYY-MM-DD | Range start date |
| `to_date` | YYYY-MM-DD | Range end date |
| `use_historical_party` | boolean | Attribute MP donations to party at time of donation (default: true) |

**Example:** Get party donations for the 2010-2015 parliament with historical attribution:
```
GET /api/v2/aggregates/party-donations/?from_date=2010-05-06&to_date=2015-05-07&use_historical_party=true
```

---

## Appendix D: Model Changes Summary (Updated)

The following model changes are required to implement the architectural improvements:

### Entity Resolution Fields (Actor model)

```python
# New fields on Actor
name_normalized = models.CharField(max_length=512, db_index=True, blank=True)
canonical_actor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
is_canonical = models.BooleanField(default=True, db_index=True)
resolution_confidence = models.FloatField(null=True, blank=True)
resolution_method = models.CharField(max_length=50, blank=True)
```

### Non-Destructive Merge Fields (Donation/Consultancy models)

```python
# New fields on Donation
canonical_donor = models.ForeignKey('Actor', null=True, blank=True, related_name='canonical_donations_made')
canonical_recipient = models.ForeignKey('Actor', null=True, blank=True, related_name='canonical_donations_received')
donor_resolution_confidence = models.FloatField(null=True, blank=True)
recipient_resolution_confidence = models.FloatField(null=True, blank=True)
resolution_date = models.DateTimeField(null=True, blank=True)

# Same pattern for Consultancy
canonical_client = models.ForeignKey('Actor', null=True, blank=True)
canonical_agency = models.ForeignKey('Actor', null=True, blank=True)
```

### Weighted Alias Fields (OtherName model)

```python
# New fields on OtherName
name_normalized = models.CharField(max_length=512, db_index=True, blank=True)
alias_type = models.CharField(max_length=20, choices=ALIAS_TYPES, default='strong', db_index=True)
```

### Party Affiliation Fields (Person model)

```python
# New field on Person
current_party = models.ForeignKey('Organization', null=True, blank=True, on_delete=models.SET_NULL)

# New model
class PartyMembership(Dateframeable, Timestampable, models.Model):
    person = models.ForeignKey('Person', related_name='party_history')
    party = models.ForeignKey('Organization', limit_choices_to={'classification': 'Political Party'})
```

---

*Document End - Version 1.1*
