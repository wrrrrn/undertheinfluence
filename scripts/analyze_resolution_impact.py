
import os
import sys
import django
from django.db import connection

# Setup Django environment
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "undertheinfluence.settings")
django.setup()

def run_query(query, params=None):
    with connection.cursor() as cursor:
        cursor.execute(query, params)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def print_table(data, columns, title):
    if not data:
        print(f"\nNo data found for: {title}")
        return

    print(f"\n{title}")
    print("=" * 80)
    
    # Calculate widths
    widths = {col: len(col) for col in columns}
    for row in data:
        for col in columns:
            val = str(row.get(col, ''))
            widths[col] = max(widths[col], len(val))
    
    # Header
    header = " | ".join(f"{col:<{widths[col]}}" for col in columns)
    print(header)
    print("-" * len(header))
    
    # Rows
    for row in data:
        print(" | ".join(f"{str(row.get(col, '')):<{widths[col]}}" for col in columns))
    print("\n")

def analyze_impact():
    print("Running Canonical Resolution Impact Analysis...\n")

    # 1. Resolution Progress
    print("1. Resolution Progress")
    progress_query = """
    SELECT
        'Meeting Attendees' as dataset,
        COUNT(*) as total,
        COUNT(canonical_actor_id) as resolved,
        ROUND(100.0 * COUNT(canonical_actor_id) / COUNT(*), 1) as pct
    FROM datafetch_meetingattendee
    UNION ALL
    SELECT
        'Donations (Donor)',
        COUNT(*),
        COUNT(canonical_donor_id),
        ROUND(100.0 * COUNT(canonical_donor_id) / COUNT(*), 1)
    FROM datafetch_donation
    WHERE donor_id IS NOT NULL
    """
    progress_data = run_query(progress_query)
    print_table(progress_data, ['dataset', 'total', 'resolved', 'pct'], "Resolution Rates")

    # 2. Donor Aggregation Impact
    # Shows who gained the most value from consolidation
    donor_impact_query = """
    WITH original_stats AS (
        SELECT donor_id, SUM(value) as val FROM datafetch_donation 
        WHERE donor_id IS NOT NULL GROUP BY donor_id
    ),
    canonical_stats AS (
        SELECT COALESCE(canonical_donor_id, donor_id) as final_id, SUM(value) as val 
        FROM datafetch_donation WHERE donor_id IS NOT NULL 
        GROUP BY COALESCE(canonical_donor_id, donor_id)
    )
    SELECT 
        a.name,
        orig.val as original_value,
        canon.val as canonical_value,
        (canon.val - COALESCE(orig.val, 0)) as value_gained,
        ROUND(((canon.val - COALESCE(orig.val, 0)) / NULLIF(orig.val, 0)) * 100, 1) as pct_gain
    FROM canonical_stats canon
    JOIN datafetch_actor a ON canon.final_id = a.id
    LEFT JOIN original_stats orig ON orig.donor_id = canon.final_id
    WHERE (canon.val - COALESCE(orig.val, 0)) > 0
    ORDER BY value_gained DESC
    LIMIT 15
    """
    donor_data = run_query(donor_impact_query)
    # Format currency
    for r in donor_data:
        r['original_value'] = f"£{r['original_value']:,.0f}" if r['original_value'] else "£0"
        r['canonical_value'] = f"£{r['canonical_value']:,.0f}"
        r['value_gained'] = f"£{r['value_gained']:,.0f}"
        r['pct_gain'] = f"{r['pct_gain']}%"
    
    print_table(donor_data, ['name', 'original_value', 'canonical_value', 'value_gained', 'pct_gain'], "Top Donor Aggregation Gains (Money)")

    # 3. Meeting Attendee Aggregation Impact
    # Shows who attended more meetings after consolidation
    meeting_impact_query = """
    WITH original_stats AS (
        SELECT actor_id, COUNT(*) as count FROM datafetch_meetingattendee 
        GROUP BY actor_id
    ),
    canonical_stats AS (
        SELECT COALESCE(canonical_actor_id, actor_id) as final_id, COUNT(*) as count 
        FROM datafetch_meetingattendee 
        GROUP BY COALESCE(canonical_actor_id, actor_id)
    )
    SELECT 
        a.name,
        orig.count as original_count,
        canon.count as canonical_count,
        (canon.count - COALESCE(orig.count, 0)) as meetings_gained
    FROM canonical_stats canon
    JOIN datafetch_actor a ON canon.final_id = a.id
    LEFT JOIN original_stats orig ON orig.actor_id = canon.final_id
    WHERE (canon.count - COALESCE(orig.count, 0)) > 0
    ORDER BY meetings_gained DESC
    LIMIT 15
    """
    meeting_data = run_query(meeting_impact_query)
    print_table(meeting_data, ['name', 'original_count', 'canonical_count', 'meetings_gained'], "Top Meeting Attendee Aggregation Gains (Count)")

    # 4. "Shattered" Identities (Most aliases merged)
    alias_query = """
    SELECT 
        canon.name,
        COUNT(DISTINCT ma.actor_id) as alias_count
    FROM datafetch_meetingattendee ma
    JOIN datafetch_actor canon ON ma.canonical_actor_id = canon.id
    WHERE ma.actor_id != ma.canonical_actor_id
    GROUP BY canon.id, canon.name
    ORDER BY alias_count DESC
    LIMIT 10
    """
    alias_data = run_query(alias_query)
    print_table(alias_data, ['name', 'alias_count'], "Most Fragmented Identities (by Alias Count)")

if __name__ == "__main__":
    analyze_impact()
