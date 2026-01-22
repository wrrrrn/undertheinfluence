# Political Influence Data Analysis Queries

This directory contains SQL analysis queries for the UnderTheInfluence database, split by analysis focus area.

## Overview

The queries have been organized into focused files based on analytical perspective:

| File | Focus | Key Questions Answered |
|------|-------|----------------------|
| `01_donor_analysis.sql` | **Who gives** | Donor concentration, whale donors, repeat donors, Gini coefficient |
| `02_party_funding.sql` | **Party financing** | Which parties get most funding, from whom, donor concentration by party |
| `03_mp_ministerial_funding.sql` | **MPs & ministers** | Individual MP funding, ministerial portfolios, government departments |
| `04_committee_funding.sql` | **Parliamentary committees** | Select committee member donations, industry-specific committees |
| `05_sector_analysis.sql` | **Industry sectors** | Who is lobbying whom in agriculture, finance, energy, healthcare, etc. |
| `06_lobbying_overlap.sql` | **Lobbying + donations** | Organizations that both lobby AND donate, influence triangles |
| `07_organizational_flows.sql` | **Org-to-org flows** | Organizational donation patterns, bidirectional flows |
| `08_summary_stats.sql` | **Database overview** | Record counts, data quality, classification statistics |
| `09_grassroots_funding.sql` | **Grassroots funding** | Analysis EXCLUDING whale donors (£500K+) and trade unions |
| `10_mp_lobbying_connections.sql` | **MP-lobbying links** | MPs connected to lobbying clients |
| `11_ministerial_meetings.sql` | **Ministerial access** | GOV.UK transparency data, lobbying practitioners, influence triangle |
| `12_lobby_employee_analysis.sql` | **Lobbying practitioners** | Staff analysis, former MPs/SPADs, practitioner networks |
| `13_director_psc_analysis.sql` | **Corporate ownership** | Directors, beneficial owners, corporate consolidation, revolving door |

## Quick Start

### Running Individual Queries

Connect to your PostgreSQL database and run queries from any file:

```bash
# Via Docker
docker compose exec -T db psql -U uti -d uti < analysis/01_donor_analysis.sql > output/donor_analysis.txt

# Direct connection
psql -U uti -d uti -f analysis/02_party_funding.sql

# Run specific query by line numbers
sed -n '25,50p' analysis/03_mp_ministerial_funding.sql | psql -U uti -d uti
```

### Running All Queries in a File

```bash
# Output to file
psql -U uti -d uti -f analysis/01_donor_analysis.sql -o results_donor.txt

# Output to CSV
psql -U uti -d uti -f analysis/02_party_funding.sql --csv -o results_party.csv
```

## File Descriptions

### 01 - Donor Analysis

**Focus**: Concentration and dominance patterns in political donations

**Sections**:
1. Top Donors - Who gives the most across all recipients
2. Concentration Metrics - Whale donors vs long tail, Gini coefficient, top 1% vs 99%
3. Donor Type Breakdown - Individual vs organizational giving
4. Repeat Donors - One-time vs multi-donation patterns
5. Donor Diversity - How many different recipients do donors fund?

**Key Queries**:
- `1.1` - Top 50 donors by total value
- `2.1` - Whale donors vs long tail distribution (£1M+, £500K-£1M, etc.)
- `2.2` - Top 1% vs Bottom 99% concentration
- `2.3` - Gini coefficient for donation inequality
- `4.1` - Donor frequency distribution (one-time vs repeat)

**Use Cases**:
- Identify major financial players in UK politics
- Measure concentration of political funding
- Understand repeat vs one-time donor behavior

---

### 02 - Party Funding

**Focus**: Political party financing from donor and temporal perspectives

**Sections**:
1. Party-Level Overview - Total funding, market share
2. Donor Type Breakdown by Party - Individual vs organizational funding per party
3. Top Donors to Each Party - Who funds each major party
4. Temporal Trends - Year-over-year funding patterns
5. Donor Concentration by Party - Top 10 donors' share of each party
6. Cross-Party Donors - Who funds multiple parties?

**Key Queries**:
- `1.1` - Top parties by total donations received
- `1.2` - Party funding market share (% of total party donations)
- `2.1` - Party donations by donor type (individuals, trade unions, companies, etc.)
- `4.1` - Party donations by year (temporal trends)
- `5.1` - Top 10 donors' share of each party's funding
- `6.1` - Donors who fund multiple parties

**Use Cases**:
- Compare party funding levels
- Identify party dependencies on specific donor types
- Spot non-partisan donors funding multiple parties

---

### 03 - MP & Ministerial Funding

**Focus**: Individual MPs and government ministers from funding perspective

**Sections**:
1. Individual MP Analysis - Top recipients, MPs by party
2. Ministerial Portfolio Analysis - Current ministers, donations by department
3. Home Office Deep Dive - Example department analysis
4. Temporal Analysis - Donations before/during/after ministerial appointments
5. Summary Statistics - Ministers vs non-ministers

**Key Queries**:
- `1.1` - Top 50 MPs/Lords by donations received
- `1.2` - MPs by party - total donations per party's MPs
- `2.1` - Current ministers and their donations
- `2.2` - Donations by government department (Home Office, Treasury, Foreign Office, etc.)
- `2.3` - Ministerial rank analysis (Cabinet vs Junior Ministers vs PPSs)
- `2.4` - Donations during ministerial tenure (date-filtered)
- `2.5` - Top donors to current ministers
- `4.1` - Donation pattern changes around ministerial appointments

**Use Cases**:
- Identify which MPs receive most funding
- Analyze funding to specific government departments (e.g., who funds Home Office ministers?)
- Track donation changes when MPs enter/leave government

---

### 04 - Committee Funding

**Focus**: Parliamentary committee member donations

**Sections**:
1. Select Committee Overview - Membership and donation statistics
2. Departmental Select Committees - Major committees (Home Affairs, Treasury, etc.)
3. Industry-Specific Committee Analysis - Treasury (finance), DEFRA (agriculture), etc.
4. Committee Member vs Non-Member Comparison
5. Cross-Committee Analysis - MPs on multiple committees
6. Summary Statistics

**Key Queries**:
- `1.2` - All committees with member counts and donation totals
- `2.1` - Major departmental select committees - member funding
- `2.2` - Committee chairs - funding analysis
- `3.1` - Financial sector donations to Treasury Committee members
- `3.2` - Agriculture sector donations to DEFRA Committee members
- `4.1` - Do committee members receive more funding than non-members?
- `5.2` - MPs who serve on committees AND hold ministerial roles

**Use Cases**:
- Analyze funding to MPs scrutinizing specific industries
- Identify potential conflicts of interest (e.g., finance sector funding Treasury Committee)
- Compare funding levels for committee vs non-committee MPs

**TODO**:
- APPG (All-Party Parliamentary Group) membership data not yet imported
- Once available, add similar queries for APPG members
- See top of file for import requirements

---

### 05 - Sector Analysis

**Focus**: Industry sector funding patterns - who lobbies whom in specific sectors

**Sections**:
1. Sector Identification & Classification - Categorize donors by industry
2. Sector-Level Donation Analysis - Overall breakdown by sector
3. Agriculture Sector Deep Dive - Farm/food industry donations
4. Financial Services Sector Deep Dive - Banking/finance donations
5. Energy Sector Deep Dive - Energy/oil/gas donations
6. Healthcare & Pharma Sector Deep Dive
7. Technology Sector Deep Dive
8. Cross-Sector Analysis - Which sectors fund which parties?
9. **Defense & Aerospace Sector Deep Dive** - Military contractors, Defence Committee
10. **Transport & Logistics Sector Deep Dive** - Rail, aviation, shipping, Transport Committee
11. **Real Estate & Property Sector Deep Dive** - Developers, Housing Ministers
12. **Retail & Consumer Goods Sector Deep Dive**
13. **Media & Broadcasting Sector Deep Dive** - DCMS Committee
14. **Gambling & Betting Sector Deep Dive**
15. **Tobacco & Alcohol Sector Deep Dive**

**Key Queries**:
- `1.1` - Donor organizations by inferred sector
- `2.1` - Donations by sector - overall breakdown
- `3.1` - Agriculture donors - who they fund
- `3.2` - Agriculture sector - top recipients (MPs/parties)
- `3.3` - Agriculture sector funding to DEFRA Committee members
- `4.1` - Financial services donors - who they fund
- `4.2` - Financial services funding to Treasury Committee members
- `5.1` - Energy sector donors - who they fund
- `6.1` - Healthcare/pharma donors - who they fund
- `8.1` - Sector funding by recipient type (parties vs MPs)
- `8.2` - Which sectors fund which parties most?
- **`9.1`** - Defense & aerospace donors
- **`9.2`** - Defense funding to Defence Committee members
- **`9.3`** - Defense funding to Defence Ministers
- **`10.1`** - Transport sector donors
- **`10.2`** - Transport funding to Transport Committee members
- **`10.3`** - Aviation subsector specific analysis
- **`11.1`** - Real estate & property donors
- **`11.2`** - Property developer top recipients
- **`11.3`** - Housing Ministers & property funding
- **`13.1`** - Media & broadcasting donors
- **`13.2`** - Media funding to DCMS Committee members
- **`14.1`** - Gambling & betting donors
- **`15.1`** - Tobacco & alcohol donors

**Sector Classifications**:
- Financial Services (banks, investment, insurance)
- Agriculture & Food
- Energy & Utilities
- Technology & Telecom
- Healthcare & Pharma
- Real Estate & Construction
- Manufacturing & Industrial
- Transport & Logistics (rail, aviation, shipping)
- **Defense & Aerospace** (military contractors, arms manufacturers)
- **Retail & Consumer Goods**
- **Media & Broadcasting** (newspapers, TV, radio, publishing)
- **Gambling & Betting** (casinos, bookmakers)
- **Tobacco & Alcohol** (breweries, distilleries)
- Trade Unions
- Lobbying & PR

**Use Cases**:
- Answer "Who is lobbying whom in agriculture?"
- Identify industry-specific influence patterns
- Spot potential conflicts (e.g., pharma funding health ministers)
- Track which industries support which parties

---

### 06 - Lobbying Overlap

**Focus**: Intersection of lobbying activity and political donations

**Sections**:
1. Organizations That Both Lobby AND Donate
2. Lobbying Agencies with Clients Who Also Donate
3. MPs Receiving Donations from Lobbying Clients
4. Donor-Agency-Recipient "Influence Triangles"
5. Top Lobbying Agencies by Client Count
6. Summary Statistics - Lobbying-Donation Overlap
7. Recipients of Lobbying-Client Donations (Breakdown by Type)
8. Lobbying-Donating Organizations by Type

**Key Queries**:
- `2.1` - Organizations that both lobby AND donate
- `2.2` - Lobbying agencies with clients who also donate
- `2.3` - MPs receiving donations from lobbying clients
- `2.4` - Donor-Agency-Recipient "influence triangles" (£10K+ donations)
- `2.5` - Top lobbying agencies by client count
- `2.6` - Summary: How many orgs both lobby and donate?
- `2.7` - Who receives donations from lobbying clients? (MPs, parties, orgs)
- `2.8` - Lobbying-donating organizations by type

**Important**: All queries use **non-inflating joins** to avoid cartesian products from multiple donations/consultancies per relationship.

**Use Cases**:
- Identify organizations exerting influence through both lobbying AND donations
- Map "influence triangles" (donor → lobbying agency → recipient MP)
- Quantify overlap between lobbying and donation ecosystems

---

### 07 - Organizational Flows

**Focus**: Donation flows between organizations and bidirectional patterns

**Sections**:
1. Organizations as Donors
2. Organizations as Recipients
3. Organizations Both Giving and Receiving
4. Organization-to-Organization Donations
5. Individual Donations (Person-to-Person)
6. MPs with Current Memberships - Donations Received
7. Bidirectional Flow Analysis (Donation Flow Matrix by Actor Type)
8. Party-to-Individual Donation Flows
9. Organization-to-Individual Donation Flows (Non-Party)

**Key Queries**:
- `4.1` - Top 50 organizations as donors
- `4.2` - Top 50 organizations as recipients
- `4.3` - Organizations both giving and receiving (excluding parties)
- `4.4` - Organization-to-organization donations
- `6.1` - Donation flow matrix by actor type (Individual/Party/Organization)
- `6.2` - Party-to-individual donation flows
- `6.3` - Organization-to-individual flows (non-party)

**Use Cases**:
- Map organizational donation networks
- Understand bidirectional flows (who gives to whom)
- Identify organizations acting as intermediaries

---

### 08 - Summary Stats

**Focus**: Database overview, data quality, and aggregate statistics

**Sections**:
1. Database Overview - Record counts
2. Date Range Coverage
3. Sector & Classification Analysis
4. Data Quality Checks (Null Analysis)
5. Time-Based Analysis (Donations by Year)

**Key Queries**:
- `9.1` - Database overview (total persons, orgs, donations, consultancies, etc.)
- `9.2` - Date range coverage (earliest/latest donations)
- `7.1` - Donations by donor classification
- `7.2` - Lobbying clients by classification
- `8.1` - Null donor analysis by donation type
- `A.1` - Donations by year (lobbying clients only)

**Use Cases**:
- Get high-level database statistics
- Check data quality and completeness
- Understand temporal coverage

---

### 09 - Grassroots Funding (Excluding Whales & Unions)

**Focus**: Donations EXCLUDING mega-donors and trade unions to see grassroots patterns

**Exclusions Applied**:
- **Whale Donors**: Donors with £500K+ lifetime total donations
- **Trade Unions**: All organizations classified as 'Trade Union'
- **Large Single Donations**: Optional filtering of donations >=£50K

**Sections**:
1. Define Exclusions - What's being filtered out and impact
2. Grassroots Donor Analysis - Top grassroots donors, concentration metrics
3. Party Funding Without Whales & Unions - Clean party comparison
4. MP Funding Without Whales & Unions - MP grassroots support
5. Sector Analysis (Grassroots Donors Only)
6. Small Donor Analysis - Under £1,000 donations
7. Summary Statistics - Overall impact of exclusions

**Key Queries**:
- `0.1` - Identify whale donors and unions being excluded
- `1.1` - Top 50 grassroots donors (excluding whales/unions)
- `1.2` - Grassroots donor concentration (£100K-£500K max bracket)
- `1.3` - Individual-only donors (no organizations, under £50K donations)
- `2.1` - Party funding (grassroots only)
- `2.2` - **Party funding comparison: With vs without whales/unions**
- `2.3` - **Which parties depend most on whales/unions?**
- `3.1` - Top MPs by grassroots donations
- `3.2` - Ministers: Grassroots vs whale/union funding
- `5.1` - Small donors only (under £1,000 per donation)
- `5.2` - Parties ranked by small donor count
- `6.1` - Overall impact summary statistics

**Why This Matters**:
Whale donors and trade unions can dominate donation statistics, masking patterns from smaller individual donors and grassroots organizations. This analysis reveals:
- Which parties/MPs have genuine grassroots support
- Dependency on mega-donors vs broad-based funding
- True individual donor engagement levels

**Use Cases**:
- Compare party grassroots strength
- Identify MPs with broad vs concentrated support
- Understand vulnerability to losing large donors
- Find genuinely popular politicians by small donor count

**Example Insight**:
Query `2.3` shows which parties would lose most funding if whales/unions withdrew - revealing strategic funding vulnerabilities.

---

### 11 - Ministerial Meetings & Lobbying Practitioners

**Focus**: GOV.UK ministerial transparency data and lobbying practitioner networks

**Data Coverage**: 7,183 meetings across 8 departments (as of Jan 2026)
- DBT (2,172), DSIT (1,211), Home Office (798), DWP (793)
- DfT (782), DHSC (543), MoJ (532), DfE (352)

**Sections**:
1. Ministerial Meetings Overview - Meetings by department, top external actors, top ministers
2. Meeting Topics & Patterns - Keyword analysis, tech vs child safety comparison
3. Lobbying Infrastructure - Agency statistics, client counts, practitioner headcounts
4. The Influence Triangle - Organizations using meetings + lobbying + donations
5. Tech Giants' Lobbying Networks - Which agencies do Google, Meta, etc. use?
6. Trade Unions - Full Spectrum Influence - Unions using all three channels
7. Lobbying Practitioners - Total counts, notable names (revolving door)
8. Specific Organization Deep Dives - Google's full influence profile
9. Summary Statistics - Cross-reference analysis

**Key Queries**:
- `1.1` - Total meetings by department
- `1.2` - Top 50 external actors by ministerial access
- `1.3` - Top ministers by meeting count
- `2.1` - Meeting topics by keyword analysis
- `2.2` - Tech company meetings vs child safety group meetings
- `4.1` - Organizations with BOTH ministerial meetings AND lobbying clients
- `4.2` - Full influence triangle: meetings + lobbying + donations
- `5.1` - Which lobbying agencies do tech giants use?
- `6.1` - Trade unions with meetings, lobbying, AND donations
- `7.3` - Search for notable political names in lobbying practitioners
- `8.1-8.3` - Google's full influence profile (meetings, agencies, donations)
- `9.2` - Cross-reference summary: How many orgs use multiple influence channels?

**Key Findings** (from Jan 2026 analysis):
- **Google** leads tech with 21 meetings, 13 ministers, using 6 lobbying agencies
- **UNISON** is the top "triple influencer" (16 meetings, lobbying, £44M donated)
- **AI dominates** ministerial discussions (1,207 meetings, 17% of total)
- **Alastair Campbell** (former Blair advisor) registered as practitioner at Portland
- **Pharma uses more agencies** (7-8 each) than tech (1-6) due to regulatory complexity

**Use Cases**:
- Identify who has most access to government ministers
- Track the "revolving door" between politics and lobbying
- Map organizations using multiple influence channels
- Compare sectors' lobbying strategies (tech vs pharma vs unions)
- Analyze ministerial meeting topics over time

---

### 13 - Director & PSC (Beneficial Owner) Analysis

**Focus**: Companies House director and beneficial owner data for lobbying agencies

**Data Source**: Companies House Officers API and PSC API via `enrich_companies_house --fetch-all`

**Sections**:
1. Multi-Agency Directors - People directing multiple lobbying agencies
2. Largest Boards - Agencies with most directors
3. Beneficial Ownership Concentration - Breakdown of ownership stakes
4. Owner-Operators - Directors who also own significant stakes
5. Corporate Ownership (Holding Companies) - Agencies owned by corporate entities
6. Parent Companies - Holding companies owning multiple agencies
7. Revolving Door - Former MPs who became lobbying agency directors
8. Lobbying Agencies in Ministerial Meetings - Overlap analysis
9. Ministers Meeting Lobbying Agencies - Which ministers meet lobbied agencies
10. Meeting Details - Full meeting records with lobbying agencies
11. Summary Statistics - High-level counts for director/PSC data
12. Director Network - Shared directorships between agencies

**Key Queries**:
- `1` - People directing multiple lobbying agencies (potential coordination)
- `2` - Agencies with largest boards (>3 directors)
- `3` - Beneficial ownership breakdown (25-50%, 50-75%, 75-100% stakes)
- `4` - Owner-operators (directors who also own significant stakes)
- `5-6` - Corporate ownership chains and holding company networks
- `7` - Former MPs who became lobbying directors (revolving door)
- `8-10` - Ministerial meeting overlap with lobbying agencies
- `11` - Summary statistics (396 directors, 231 PSCs as of Jan 2026)
- `12` - Shared directorship network (agencies connected by common directors)

**Key Findings** (from Jan 2026 import):
- **396 directors** imported across 196 lobbying agencies
- **231 beneficial owners** (PSCs) identified
- **2 former MPs** now directing lobbying agencies (revolving door)
- **Corporate consolidation** patterns identified via holding companies

**Use Cases**:
- Identify corporate consolidation in lobbying industry
- Track the "revolving door" between Parliament and lobbying
- Map ownership structures and hidden connections
- Find shared directorship networks suggesting coordination
- Correlate ownership with ministerial access

---

## Query Conventions

All queries follow these conventions:

1. **Actor IDs, not names**: Group by `actor.id` to avoid split/merge artifacts from name changes
2. **Safe date casting**: Only cast dates matching `YYYY-MM-DD` regex to avoid errors on partial dates
3. **Non-inflating joins**: Pre-aggregate donations and consultancies separately before joining
4. **Stable CTEs**: Use Common Table Expressions (WITH clauses) for readability

## Database Schema Reference

Key tables used in these queries:

- `datafetch_actor` - Base table for all entities (polymorphic: Person OR Organization)
- `datafetch_person` - Individual people (MPs, Lords, donors)
- `datafetch_organization` - Organizations (parties, companies, trade unions, etc.)
- `datafetch_donation` - Financial donations (donor_id → recipient_id)
- `datafetch_consultancy` - Lobbying relationships (client_id → agency_id)
- `datafetch_membership` - Organizational memberships (person_id → organization_id)
  - Includes MP party affiliations, committee memberships, ministerial roles

## Tips & Best Practices

### Running Specific Queries

Most files contain multiple numbered queries. Extract and run specific ones:

```bash
# Run query 2.1 from sector analysis (lines 45-95 for example)
sed -n '45,95p' analysis/05_sector_analysis.sql | psql -U uti -d uti
```

### Exporting Results

```bash
# Export to CSV
psql -U uti -d uti -f analysis/01_donor_analysis.sql --csv -o donor_analysis_$(date +%Y%m%d).csv

# Export to JSON
psql -U uti -d uti -t -A -F"," -f analysis/02_party_funding.sql | python -c "import csv, json, sys; print(json.dumps([dict(r) for r in csv.DictReader(sys.stdin)], indent=2))" > party_funding.json
```

### Performance

- Most queries include appropriate `LIMIT` clauses
- CTEs are used for readability, not performance (PostgreSQL optimizes them)
- For very large result sets, consider adding pagination with `OFFSET`/`LIMIT`

### Modifying Queries

Common modifications:

1. **Change time period**: Update date filters (e.g., `>= DATE '2020-01-01'`)
2. **Adjust thresholds**: Modify value brackets in concentration queries
3. **Add specific organizations**: Filter by `actor.name LIKE '%YourOrg%'`
4. **Change result limit**: Adjust `LIMIT 50` to your needs

## Data Limitations

### Current Gaps

1. **APPG Memberships**: Not yet imported (63 APPGs exist but 0 membership records)
   - See `04_committee_funding.sql` TODO at top of file
   - Import needed from: https://www.parliament.uk/...register-of-all-party-parliamentary-groups/

2. **Partial Dates**: Some dates are YYYY or YYYY-MM format, not full YYYY-MM-DD
   - Queries use safe casting with regex validation

3. **Classification Inconsistencies**: Some organizations lack classification
   - Queries use `COALESCE(classification, 'Unclassified')`

### Known Issues

See `docs/DATA_QUALITY_REPORT.md` for comprehensive quality analysis.

## Next Steps

### Recommended Query Additions

1. **Temporal Deep Dives**:
   - Election cycle analysis (donations spike before elections?)
   - Ministerial appointment impact (donations change when MP becomes minister?)

2. **Network Analysis**:
   - Shared donor networks between MPs
   - Lobbying agency client portfolios

3. **Geographic Analysis**:
   - Donations by constituency region
   - Regional industry influence patterns

4. **APPG Analysis** (once membership data imported):
   - Donations to APPG members by topic area
   - Industry-APPG funding correlations

### Related Documentation

- **Data Import**: `docs/DATA_IMPORT_GUIDE.md`
- **Data Quality**: `docs/DATA_QUALITY_REPORT.md`
- **Data Models**: `docs/data-models.md`
- **System Architecture**: `docs/systems-architecture.md`

## Contributing

When adding new queries:

1. Add them to the appropriate file (or create new file if needed)
2. Follow naming convention: `##_descriptive_name.sql`
3. Include comments explaining what the query does
4. Update this README with query description
5. Test on actual database before committing

## Questions?

- Check existing query comments for inline documentation
- Review `docs/data-models.md` for schema details
- See `CLAUDE.md` for project overview

---

**Last Updated**: 2026-01-22
