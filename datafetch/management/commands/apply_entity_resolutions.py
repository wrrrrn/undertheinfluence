"""
Apply Approved Entity Resolutions

Applies approved ActorResolution records by setting canonical_actor
fields on MeetingAttendee records.

Never modifies original data - only sets the canonical pointer.

Phase 3: Entity Resolution
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q
from datafetch import models
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Apply approved entity resolutions to meeting attendee records'

    def add_arguments(self, parser):
        parser.add_argument(
            '--auto-approve-threshold',
            type=float,
            help='Auto-approve resolutions with confidence >= this value before applying'
        )
        parser.add_argument(
            '--resolution-id',
            type=int,
            help='Apply specific resolution by ID'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes'
        )

    def handle(self, *args, **options):
        auto_approve_threshold = options.get('auto_approve_threshold')
        resolution_id = options.get('resolution_id')
        dry_run = options.get('dry_run', False)

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Apply Entity Resolutions (Optimized)")
        self.stdout.write(f"{'='*60}\n")

        # Get approved resolutions
        resolutions_qs = models.ActorResolution.objects.all()
        
        if resolution_id:
            resolutions_qs = resolutions_qs.filter(id=resolution_id)
            if not resolutions_qs.exists():
                self.stderr.write(f"Resolution {resolution_id} not found")
                return
        else:
            # Auto-approve if threshold provided
            if auto_approve_threshold:
                pending = models.ActorResolution.objects.filter(
                    review_status='pending',
                    confidence__gte=auto_approve_threshold
                )

                if pending.exists():
                    count = pending.count()
                    self.stdout.write(f"Auto-approving {count} resolutions >= {auto_approve_threshold} confidence...")

                    if not dry_run:
                        pending.update(
                            review_status='approved',
                            decision='auto_merge'
                        )

            # Get all approved resolutions
            resolutions_qs = resolutions_qs.filter(
                review_status='approved'
            ).exclude(
                decision='ignore'
            )

        total_resolutions = resolutions_qs.count()

        if total_resolutions == 0:
            self.stdout.write(self.style.WARNING("No approved resolutions to apply"))
            return

        self.stdout.write(f"Processing {total_resolutions} resolutions...")

        # 1. Build the merge map and target actor cache
        # duplicate_id -> canonical_id
        merge_map = {}
        actor_cache = {} # id -> Actor object
        
        # Prefetch to avoid N+1
        resolutions = resolutions_qs.select_related('actor1', 'actor2', 'canonical_actor')
        
        for res in resolutions:
            canon = res.canonical_actor
            if not canon:
                continue
            
            # Cache the actors for later use
            actor_cache[res.actor1_id] = res.actor1
            actor_cache[res.actor2_id] = res.actor2
            actor_cache[canon.id] = canon
            
            # Identify which one is the duplicate (the one that ISN'T the canonical)
            duplicate_id = res.actor2_id if res.actor1_id == canon.id else res.actor1_id
            merge_map[duplicate_id] = canon.id

        # 2. Flatten the chains (e.g., if A->B and B->C, then A->C)
        final_mapping = {} # duplicate_id -> final_canonical_id
        for dup_id in merge_map:
            path = [dup_id]
            curr = dup_id
            visited = {curr}
            
            while curr in merge_map:
                next_id = merge_map[curr]
                if next_id in visited: # Cycle detection
                    break
                curr = next_id
                visited.add(curr)
                path.append(curr)
            
            final_target_id = curr
            final_mapping[dup_id] = final_target_id

        # 3. Group by the final master target
        # final_canonical_id -> set(duplicate_actors)
        canonical_groups = {}
        for dup_id, master_id in final_mapping.items():
            if dup_id == master_id:
                continue
                
            if master_id not in canonical_groups:
                canonical_groups[master_id] = {
                    'canonical': actor_cache[master_id],
                    'merged': set()
                }
            canonical_groups[master_id]['merged'].add(actor_cache[dup_id])

        self.stdout.write(f"Flattened chains into {len(canonical_groups)} master groups.")

        # Statistics
        stats = {
            'groups_processed': 0,
            'attendees_updated': 0,
            'donors_updated': 0,
            'recipients_updated': 0,
            'clients_updated': 0,
            'agencies_updated': 0,
        }

        # 4. Process each master group
        for master_id, group in canonical_groups.items():
            canonical = group['canonical']
            merged_actors = list(group['merged'])
            
            self.stdout.write(f"  Master Merge: {len(merged_actors)} aliases -> {canonical.name} ({master_id})")

            if not dry_run:
                with transaction.atomic():
                    # 1. Update MeetingAttendee (actor)
                    updated_attendees = models.MeetingAttendee.objects.filter(
                        actor__in=merged_actors
                    ).update(canonical_actor=canonical)

                    # 2. Update Donation (donor)
                    updated_donors = models.Donation.objects.filter(
                        donor__in=merged_actors
                    ).update(canonical_donor=canonical)

                    # 3. Update Donation (recipient)
                    updated_recipients = models.Donation.objects.filter(
                        recipient__in=merged_actors
                    ).update(canonical_recipient=canonical)

                    # 4. Update Consultancy (client)
                    updated_clients = models.Consultancy.objects.filter(
                        client__in=merged_actors
                    ).update(canonical_client=canonical)

                    # 5. Update Consultancy (agency)
                    updated_agencies = models.Consultancy.objects.filter(
                        agency__in=merged_actors
                    ).update(canonical_agency=canonical)

                    # Update stats
                    stats['groups_processed'] += 1
                    stats['attendees_updated'] += updated_attendees
                    stats['donors_updated'] += updated_donors
                    stats['recipients_updated'] += updated_recipients
                    stats['clients_updated'] += updated_clients
                    stats['agencies_updated'] += updated_agencies

            else:
                # Dry run counts
                u_attendees = models.MeetingAttendee.objects.filter(actor__in=merged_actors).count()
                u_donors = models.Donation.objects.filter(donor__in=merged_actors).count()
                u_recipients = models.Donation.objects.filter(recipient__in=merged_actors).count()
                u_clients = models.Consultancy.objects.filter(client__in=merged_actors).count()
                u_agencies = models.Consultancy.objects.filter(agency__in=merged_actors).count()

                self.stdout.write(f"    [DRY RUN] Would update: {u_attendees} attendees, "
                                  f"{u_donors} donors, {u_recipients} recipients...")
                stats['groups_processed'] += 1
                stats['attendees_updated'] += u_attendees
                stats['donors_updated'] += u_donors
                stats['recipients_updated'] += u_recipients
                stats['clients_updated'] += u_clients
                stats['agencies_updated'] += u_agencies

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Application Summary")
        self.stdout.write(f"{'='*60}")
        self.stdout.write(self.style.SUCCESS(f"✓ Groups processed: {stats['groups_processed']}"))
        self.stdout.write(f"  Attendees updated: {stats['attendees_updated']}")
        self.stdout.write(f"  Donations updated: {stats['donors_updated']} (donor) / {stats['recipients_updated']} (recipient)")
        self.stdout.write(f"  Consultancies updated: {stats['clients_updated']} (client) / {stats['agencies_updated']} (agency)")

        if not dry_run:
            self.stdout.write("")
            self.stdout.write("Verify results:")
            self.stdout.write("  python manage.py shell")
            self.stdout.write("  >>> from datafetch.models import Donation")
            self.stdout.write("  >>> Donation.objects.filter(canonical_donor__isnull=False).count()")
        else:
            self.stdout.write(self.style.WARNING("\n[DRY RUN] No changes made to database"))

        self.stdout.write("")
