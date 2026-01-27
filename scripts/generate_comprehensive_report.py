
import os
import sys
import django
from django.db import connection
from datetime import datetime

# Setup Django
sys.path.append(os.getcwd())
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "undertheinfluence.settings")
django.setup()

def run_query(query):
    with connection.cursor() as cursor:
        cursor.execute(query)
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

def format_currency(value):
    if value >= 1_000_000:
        return f"£{value/1_000_000:.2f}M"
    if value >= 1_000:
        return f"£{value/1_000:.2f}K"
    return f"£{value:,.2f}"

def generate_report():
    print("Generating Comprehensive Analysis Report...")
    now = datetime.now().strftime("%B %d, %y")
    
    report = f"""# UnderTheInfluence - Comprehensive Data Analysis Report

**Generated:** {now}
**Database:** PostgreSQL (undertheinfluence)
**Analysis Period:** 2001-2025
**Status:** Post-Canonical Resolution & Companies House Enrichment

---

## Executive Summary

This report provides a consolidated view of political influence in the UK, leveraging the newly implemented entity resolution (canonical matching) to group duplicate actors.

### Database Overview
"""
    
    # 1. Overview
    overview = run_query("""
        SELECT 'Total Persons' AS metric, COUNT(*) AS count FROM datafetch_person
        UNION ALL SELECT 'Total Organizations', COUNT(*) FROM datafetch_organization
        UNION ALL SELECT 'Total Actors', COUNT(*) FROM datafetch_actor
        UNION ALL SELECT 'Total Donations', COUNT(*) FROM datafetch_donation
        UNION ALL SELECT 'Donations with Value > 0', COUNT(*) FROM datafetch_donation WHERE value > 0
        UNION ALL SELECT 'Ministerial Meetings', COUNT(*) FROM datafetch_ministerialmeeting
        UNION ALL SELECT 'Meeting Attendees', COUNT(*) FROM datafetch_meetingattendee
    """)
    
    report += "| Metric | Count |\n|--------|-------|\n"
    for row in overview:
        report += f"| **{row['metric']}** | {row['count']:,} |\n"
    
    # 2. CH Status
    report += "\n### Companies House Enrichment Status\n\n"
    ch_status = run_query("SELECT status, COUNT(*) as count FROM datafetch_companieshousematch GROUP BY status ORDER BY count DESC")
    report += "| Status | Count |\n|--------|-------|\n"
    for row in ch_status:
        report += f"| {row['status'].replace('_', ' ').title()} | {row['count']:,} |\n"

    # 3. Top Donors
    report += "\n---\n\n## 1. DONOR CONCENTRATION (Canonical)\n\n### 1.1 Top 10 Donors (All Time)\n\n"
    top_donors = run_query("""
        SELECT
          donor.name AS donor_name,
          COUNT(d.id) AS donation_count,
          SUM(d.value) AS total_donated
        FROM datafetch_donation d
        JOIN datafetch_actor donor ON COALESCE(d.canonical_donor_id, d.donor_id) = donor.id
        WHERE d.value > 0
        GROUP BY donor.id, donor.name
        ORDER BY total_donated DESC
        LIMIT 10
    """)
    report += "| Rank | Donor | Donations | Total Donated |\n|------|-------|-----------|---------------|\n"
    for i, row in enumerate(top_donors, 1):
        report += f"| {i} | **{row['donor_name']}** | {row['donation_count']:,} | **{format_currency(row['total_donated'])}** |\n"

    # 4. Party Funding
    report += "\n## 2. POLITICAL PARTY FUNDING\n\n"
    parties = run_query("""
        SELECT
          party.name AS party_name,
          SUM(d.value) AS total_received,
          COUNT(*) AS donation_count
        FROM datafetch_donation d
        JOIN datafetch_actor party ON COALESCE(d.canonical_recipient_id, d.recipient_id) = party.id
        JOIN datafetch_organization org ON org.actor_ptr_id = party.id
        WHERE org.classification IN ('Political Party', 'Registered Political Party', 'Registered Party') AND d.value > 0
        GROUP BY party.id, party.name
        ORDER BY total_received DESC
        LIMIT 10
    """)
    report += "| Party | Total Received | Donations |\n|-------|----------------|-----------|\n"
    for row in parties:
        report += f"| **{row['party_name']}** | **{format_currency(row['total_received'])}** | {row['donation_count']:,} |\n"

    # 5. Ministerial Access
    report += "\n## 3. MINISTERIAL MEETINGS ANALYSIS\n\n### 3.1 Top 10 Organizations by Access\n\n"
    top_access = run_query("""
        SELECT
            COALESCE(canon.name, a.name) as organization,
            COUNT(DISTINCT ma.meeting_id) as meetings
        FROM datafetch_meetingattendee ma
        JOIN datafetch_actor a ON ma.actor_id = a.id
        LEFT JOIN datafetch_actor canon ON ma.canonical_actor_id = canon.id
        GROUP BY COALESCE(ma.canonical_actor_id, ma.actor_id), COALESCE(canon.name, a.name)
        ORDER BY meetings DESC
        LIMIT 10
    """)
    report += "| Organization | Meetings |\n|--------------|----------|\n"
    for row in top_access:
        report += f"| **{row['organization']}** | {row['meetings']:,} |\n"

    # 6. Influence Triangle
    report += "\n## 4. THE INFLUENCE TRIANGLE\n\nOrganizations using Lobbying + Donations + Meetings simultaneously:\n\n"
    triangle = run_query("""
        WITH lobbying AS (
            SELECT DISTINCT COALESCE(canonical_client_id, client_id) as id FROM datafetch_consultancy
        ),
             donors AS (
            SELECT DISTINCT COALESCE(canonical_donor_id, donor_id) as id FROM datafetch_donation WHERE value > 1000
        ),
             meetings AS (
            SELECT DISTINCT COALESCE(canonical_actor_id, actor_id) as id FROM datafetch_meetingattendee
        )
        SELECT a.name, 
               (SELECT SUM(value) FROM datafetch_donation WHERE COALESCE(canonical_donor_id, donor_id) = a.id) as total_donated,
               (SELECT COUNT(DISTINCT meeting_id) FROM datafetch_meetingattendee WHERE COALESCE(canonical_actor_id, actor_id) = a.id) as meetings
        FROM datafetch_actor a
        JOIN lobbying l ON a.id = l.id
        JOIN donors d ON a.id = d.id
        JOIN meetings m ON a.id = m.id
        ORDER BY total_donated DESC
        LIMIT 10
    """)
    report += "| Organization | Total Donated | Meetings |\n|--------------|---------------|----------|\n"
    for row in triangle:
        report += f"| **{row['name']}** | {format_currency(row['total_donated'] or 0)} | {row['meetings'] or 0} |\n"

    # Save report
    with open("analysis/COMPREHENSIVE_ANALYSIS_REPORT.md", "w") as f:
        f.write(report)
    print("Report generated successfully: analysis/COMPREHENSIVE_ANALYSIS_REPORT.md")

if __name__ == "__main__":
    generate_report()
