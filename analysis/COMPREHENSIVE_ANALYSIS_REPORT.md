# UnderTheInfluence - Comprehensive Data Analysis Report

**Generated:** January 25, 2026
**Database:** PostgreSQL (undertheinfluence)
**Analysis Period:** 2001-2025 (Political Donation Data) + Ministerial Meetings
**Status:** Post-Data Cleanup & Companies House Enrichment

---

## Executive Summary

This comprehensive analysis examines political influence in the UK through detailed examination of political donations, lobbying activities, ministerial meetings, and industry sector influence. Data has been cleaned and enriched with Companies House company matching.

### Database Overview

| Metric | Count | Change |
|--------|-------|--------|
| **Total Persons** | 90,728 | +15,182 |
| **Total Organizations** | 64,337 | +1,641 |
| **Total Actors** | 155,065 | +16,823 |
| **Total Donations** | 91,513 | |
| **Donations with Value > 0** | 91,508 | |
| **Total Value Donated** | **£1.59 billion** | |
| **Total Consultancies** | 62,798 | +8,534 |
| **Total Memberships** | 136,590 | +39,954 |
| **Ministerial Meetings** | 41,362 | |
| **Meeting Attendees** | 119,793 | |
| **Directors Imported** | 62,747 | +23,961 |
| **Beneficial Owners (PSCs)** | 9,014 | +3,890 |
| **Lobbying Agency Employees** | 12,547 | +1,334 |

### Companies House Enrichment Status

| Status | Count |
|--------|-------|
| Auto-approved | 12,532 |
| Pending Review | 11,198 |
| Not Found | 16,419 |
| Not Applicable | 10,892 |
| Approved | 98 |
| Rejected | 18 |

**Total Matched:** 23,828 organizations linked to Companies House records

### Key Findings at a Glance

- **Extreme Concentration:** Just 427 whale donors (2% of all donors) control **£1.11 billion (69.7%)** of all donations
- **Institutional Dominance:** Trade unions contributed £240M+; House of Commons £157M
- **Maximum Access:** CBI leads with 482 ministerial meetings across 16 departments
- **Influence Triangle:** 48 organizations use ALL THREE channels (lobbying + donations + meetings)
- **Party Funding:** Conservative Party £607M, Labour £503M, Lib Dems £156M
- **Lobbying Workforce:** 12,547 distinct employees across 217 lobbying agencies
- **Director Networks:** 62,747 director memberships imported from Companies House

---

## 1. DONOR CONCENTRATION & DOMINANCE

### 1.1 Top 10 Donors (All Time)

| Rank | Donor | Donations | Total Donated |
|------|-------|-----------|---------------|
| 1 | **House of Commons** | 685 | **£115.24M** |
| 2 | **Unite the Union** | 953 | **£53.51M** |
| 3 | **UNISON** | 1,765 | **£44.34M** |
| 4 | **House of Commons Fees Office** | 198 | **£42.54M** |
| 5 | **GMB** | 1,683 | **£39.33M** |
| 6 | **David Sainsbury** | 177 | **£31.51M** |
| 7 | **Christopher Harborne** | 20 | **£19.22M** |
| 8 | **The Electoral Commission** | 169 | **£18.85M** |
| 9 | **National Conservative Draws Society** | 198 | **£15.36M** |
| 10 | **Union of Shop Distributive and Allied Workers** | 445 | **£13.28M** |

**Key Insights:**
- **Top 3 are institutions** (Parliament funds + Unite): £213M combined
- **Individual mega-donor pattern**: High average donations from few transactions
- **Union pattern**: Many smaller donations over sustained periods

### 1.2 Whale Donor Concentration

| Donor Bracket | Donor Count | Total Value | % of Total |
|---------------|-------------|-------------|------------|
| **£1M+** | **216** (1.0%) | **£965.91M** | **60.7%** |
| £500K-£1M | 211 (1.0%) | £143.73M | 9.0% |
| £100K-£500K | 1,214 (5.8%) | £242.51M | 15.2% |
| £50K-£100K | 1,248 (5.9%) | £82.26M | 5.2% |
| £10K-£50K | 5,612 (26.7%) | £111.78M | 7.0% |
| **Under £10K** | **12,556** (59.7%) | **£45.71M** | **2.9%** |

**Critical Finding:**
- **Top 427 donors** (216 + 211 = **2% of all donors**) control **£1.11 billion (69.7%) of all donations**
- **Bottom 12,556 donors** (60% of all donors) contribute only **£45.71M (2.9%)**

---

## 2. POLITICAL PARTY FUNDING

### 2.1 Top Parties by Total Donations Received

| Party | Total Received | Donations | Distinct Donors |
|-------|----------------|-----------|-----------------|
| **Conservative and Unionist Party** | **£607.35M** | 27,632 | 7,999 |
| **Labour Party** | **£503.25M** | 21,335 | 2,995 |
| **Liberal Democrats** | **£156.31M** | 18,768 | 4,378 |
| **Scottish National Party** | £31.31M | 815 | 214 |
| **Reform UK** | £30.19M | 248 | 102 |
| **Co-operative Party** | £21.18M | 665 | 65 |
| **UK Independence Party** | £17.84M | 1,784 | 423 |
| **Open Britain Limited** | £12.87M | 123 | 79 |
| **Vote Leave Limited** | £12.10M | 169 | 90 |
| **Green Party** | £9.95M | 1,638 | 346 |
| **Labour Together** | £8.39M | 117 | 23 |
| **Plaid Cymru** | £8.19M | 512 | 117 |

**Key Observations:**
- **Conservative + Labour** = £1.11B = **70% of all party funding**
- **Reform UK**: Only 102 donors but £121K average (extreme concentration)
- **Lib Dems**: Lowest average - most grassroots pattern

---

## 3. MINISTERIAL MEETINGS ANALYSIS

### 3.1 Meetings by Government Department

| Department | Meetings | Ministers |
|------------|----------|-----------|
| **Business, Energy & Industrial Strategy** | 7,332 | 32 |
| **Transport** | 4,332 | 35 |
| **Health and Social Care** | 3,917 | 33 |
| **Business and Trade** | 3,642 | 21 |
| **Home Office** | 2,469 | 34 |
| **Energy Security and Net Zero** | 2,305 | 17 |
| **Culture, Media and Sport** | 2,254 | 23 |
| **Science, Innovation and Technology** | 2,047 | 19 |
| **Housing, Communities and Local Government** | 2,033 | 19 |
| **Work and Pensions** | 1,926 | 25 |
| **Justice** | 1,619 | 37 |
| **Environment, Food and Rural Affairs** | 1,440 | 24 |
| **Education** | 1,109 | 24 |
| **Cabinet Office** | 1,034 | 20 |
| **HM Treasury** | 1,013 | 7 |

### 3.2 Top 20 Organizations by Ministerial Access

| Organization | Meetings | Ministers Met | Departments |
|--------------|----------|---------------|-------------|
| **Confederation of British Industry** | 482 | 73 | 16 |
| **Federation of Small Businesses** | 462 | 80 | 17 |
| **Institute of Directors** | 355 | 60 | 17 |
| **British Chambers of Commerce** | 330 | 67 | 14 |
| **British Retail Consortium** | 296 | 63 | 14 |
| **Make UK** | 290 | 56 | 11 |
| **LOCAL GOVERNMENT ASSOCIATION** | 276 | 81 | 15 |
| **Energy UK** | 266 | 43 | 13 |
| **AstraZeneca** | 254 | 52 | 9 |
| **BP** | 251 | 58 | 14 |
| **UK Hospitality** | 251 | 51 | 14 |
| **Unite** | 214 | 46 | 13 |
| **UK Finance** | 214 | 49 | 11 |
| **Network Rail** | 208 | 43 | 11 |
| **Airbus** | 203 | 57 | 16 |
| **National Grid** | 200 | 41 | 12 |
| **Shell** | 189 | 54 | 12 |
| **Airlines UK** | 178 | 34 | 10 |
| **HSBC** | 176 | 66 | 16 |
| **Barclays** | 175 | 67 | 15 |

**Key Insight:** After data cleanup, the CBI emerges as the clear leader with 482 meetings - business trade associations dominate ministerial access.

---

## 4. THE INFLUENCE TRIANGLE

### 4.1 Organizations Using ALL THREE Influence Channels

48 organizations use lobbying + donations + meetings simultaneously:

| Organization | Meetings | Agencies | Total Donated |
|--------------|----------|----------|---------------|
| **Unite the Union** | 72 | 1 | £53.51M |
| **UNISON** | 167 | 1 | £44.34M |
| **Electoral Commission** | 6 | 1 | £9.11M |
| **KPMG LLP** | 2 | 1 | £2.10M |
| **Community** | 54 | 3 | £2.02M |
| **Unite** | 214 | 1 | £0.38M |
| **Amicus** | 3 | 3 | £0.36M |
| **John Lewis** | 47 | 4 | £0.09M |
| **Manchester Airport Group** | 31 | 1 | £0.06M |
| **Community Trade Union** | 17 | 1 | £0.05M |
| **Arup** | 112 | 4 | £0.03M |
| **Road Haulage Association** | 64 | 3 | £0.03M |

**Key Insight:** Trade unions dominate the "full influence" approach - combining direct ministerial access, professional lobbying, AND political donations.

---

## 5. LOBBYING INFRASTRUCTURE

### 5.1 Top Lobbying Agencies by Client Count

| Agency | Distinct Clients | Consultancy Records |
|--------|------------------|---------------------|
| **Lexington Communications** | 1,214 | 2,760 |
| **Cratus Communications Ltd** | 941 | 1,802 |
| **Cavendish Consulting** | 901 | 2,114 |
| **Connect** | 843 | 1,942 |
| **PLMR** | 836 | 1,186 |
| **BECG** | 782 | 2,183 |
| **MHP Communications** | 732 | 1,343 |
| **Grayling** | 667 | 1,380 |
| **London Communications Agency** | 623 | 1,575 |
| **Hanover Communications** | 584 | 1,396 |
| **Four Communications** | 582 | 1,180 |
| **The Terrapin Group** | 557 | 1,577 |
| **WA Communications Ltd** | 549 | 1,126 |
| **Portland** | 526 | 933 |
| **Camlas** | 505 | 963 |

---

## 6. COMPANIES HOUSE ENRICHMENT

### 6.1 Match Quality by Category

| Category | Total Orgs | Matched | Not Found | N/A | Match % |
|----------|------------|---------|-----------|-----|---------|
| Lobbying Agency | 222 | 198 | 20 | 0 | **89.2%** |
| Lobbying Client | 22,565 | 9,624 | 5,774 | 2,233 | **42.7%** |
| Donor | 21,060 | 4,728 | 1,955 | 1,201 | **22.5%** |
| Meeting Attendee | 46,651 | 10,197 | 8,336 | 6,796 | **21.9%** |

### 6.2 Confidence Distribution

| Category | 0.95-1.00 | 0.90-0.94 | 0.85-0.89 | Auto-Approved | Pending |
|----------|-----------|-----------|-----------|---------------|---------|
| Lobbying Agency | 99.5% | 0% | 0.5% | 197 | 1 |
| Lobbying Client | 47.1% | 12.4% | 34.4% | 5,672 | 3,854 |
| Donor | 45.3% | 9.9% | 37.8% | 2,610 | 2,118 |
| Meeting Attendee | 25.6% | 21.3% | 48.6% | 4,217 | 5,976 |

---

## 7. DIRECTOR & BENEFICIAL OWNER NETWORKS

### 7.1 Companies House Data Summary

| Metric | Count |
|--------|-------|
| **Directors Imported** | 62,747 |
| **Individual PSCs (Beneficial Owners)** | 9,014 |
| **Corporate PSCs (Holding Companies)** | 9,570 |
| **Unique Directors** | 30,549 |
| **Organizations with Directors** | 14,801 |
| **Multi-Agency Directors** | 10,980 |

### 7.2 Multi-Agency Directors (Influence Brokers)

Top directors serving multiple organizations - potential influence brokers:

| Director | Orgs Directed | Example Organizations |
|----------|---------------|----------------------|
| **David Fraser Thomas** | 51 | Barratt, David Wilson Homes, Redrow |
| **Hing Lam Kam** | 35 | Northern Gas Networks, Wales & West Utilities, Northumbrian Water |
| **Duncan Macrae** | 31 | Northern Gas Networks, Wales & West Utilities |
| **Jason Michael Honeyman** | 30 | Bellway Homes, Ashberry Strategic Land |
| **Kathryn Ryan Rowbotham** | 30 | ABPI, Roche, AstraZeneca |
| **Shane Michael Doherty** | 30 | Bellway Homes, Ashberry Strategic Land |
| **Simon Scougall** | 30 | Bellway Homes, Ashberry Strategic Land |

**Key Insight:** 10,980 individuals direct multiple organizations, creating interconnected networks between energy, construction, and pharmaceutical sectors.

### 7.3 Beneficial Ownership Concentration

| Ownership Type | Count | % |
|----------------|-------|---|
| **25-50% shares** | 3,067 | 34.0% |
| **75-100% shares (full control)** | 2,942 | 32.6% |
| **Significant control** | 1,160 | 12.9% |
| **50-75% shares** | 483 | 5.4% |
| **25-50% voting rights** | 268 | 3.0% |
| Other types | 1,094 | 12.1% |

**Key Insight:** Two-thirds of beneficial owners hold either majority (75-100%) or significant minority (25-50%) stakes, indicating concentrated ownership across the political influence landscape.

### 7.4 Shared Directorships Network

Organizations sharing the most directors (potential coordination):

| Organization 1 | Organization 2 | Shared Directors |
|---------------|----------------|------------------|
| Chamber of Shipping | UK Chamber of Shipping (UKCoS) | 36 |
| techUK | TechUK | 35 |
| Association of the British Pharmaceutical Industry | ABPI variants | 30 |
| Bellway Homes | Bellway variants | 30 |

**Note:** Many shared directorships are between variant names of the same organization (data quality issue for entity resolution).

---

## 8. COMPANIES HOUSE ENRICHMENT PROGRESS

### 8.1 Match Progress by Category

| Category | Total Orgs | Auto-Approved | Pending | Not Found | N/A | Remaining |
|----------|-----------|---------------|---------|-----------|-----|-----------|
| **Lobbying Agency** | 222 | 197 | 1 | 20 | 0 | 4 |
| **Lobbying Client** | 22,569 | 5,672 | 3,854 | 5,774 | 2,233 | 4,931 |
| **Donor** | 7,921 | 2,610 | 2,118 | 1,955 | 1,201 | 37 |
| **Meeting Attendee** | 25,615 | 4,217 | 5,976 | 8,336 | 6,796 | 275 |

### 8.2 Enrichment Rate Analysis

- **Lobbying Agencies**: 89.2% matched - highest quality data
- **Lobbying Clients**: 42.2% matched - moderate quality (many informal entities)
- **Donors**: 59.7% matched - good coverage of organizational donors
- **Meeting Attendees**: 39.8% matched - challenged by international orgs, government bodies

---

## 9. ADVANCED INFLUENCE INSIGHTS

### 9.1 The "Cost of Access" Index

Organizations ranked by donation value vs ministerial meeting count:

| Organization | Total Donated | Meetings | £/Meeting | Profile |
|--------------|---------------|----------|-----------|---------|
| **House of Commons** | £115.24M | 6 | £19.2M | Transactional |
| **Unite the Union** | £53.51M | 72 | £743K | **Full Spectrum** |
| **UNISON** | £44.34M | 167 | £265K | **Full Spectrum** |
| **GMB** | £39.33M | 150 | £262K | **Full Spectrum** |
| **Communication Workers Union** | £10.03M | 38 | £264K | **Full Spectrum** |

**Influence Profiles:**
- **Full Spectrum Influence**: High donations (>£50K) AND high meetings (>10)
- **High Donor / Low Access**: Major donors with minimal meeting access
- **Expert/Lobbyist**: Low donations but frequent ministerial access

### 9.2 Cross-Departmental "Blitz" Campaigns (2024-2025)

Organizations meeting with 5+ departments in a single quarter:

| Organization | Quarter | Departments Hit |
|--------------|---------|-----------------|
| **HSBC** | 2025-Q2 | 7 |
| **Barclays** | 2025-Q2 | 6 |
| **GMB Union** | 2025-Q2 | 6 |
| **Deloitte** | 2025-Q2 | 6 |
| **Lloyds Banking Group** | 2025-Q2 | 6 |
| **Nationwide** | 2025-Q2 | 6 |
| **UNISON** | 2025-Q2 | 6 |
| **Microsoft** | 2025-Q2 | 5 |
| **Amazon** | 2025-Q2 | 5 |
| **GSK** | 2025-Q2 | 5 |

**Key Insight:** Major banks (HSBC, Barclays, Lloyds) and tech giants (Microsoft, Amazon) conduct coordinated lobbying across multiple departments simultaneously.

### 9.3 Election Cycle Dynamics (2024-2025)

Monthly donation vs meeting activity showing Purdah effects:

| Period | Donations (£M) | # Donations | # Meetings |
|--------|---------------|-------------|------------|
| 2024-06 | **£22.0M** | 1,063 | 19 |
| 2024-05 | **£29.2M** | 980 | 439 |
| 2024-07 | £5.0M | 244 | 603 |
| 2024-10 | £2.6M | 199 | **1,123** |
| 2024-11 | £3.7M | 190 | **910** |

**Key Insight:**
- **Pre-election surge**: Donations spiked to £29M in May 2024 and £22M in June 2024 (election period)
- **Purdah effect**: Meetings dropped to just 19 in June 2024 (election month) while donations surged
- **Post-election normalization**: Meetings peaked at 1,123 in October 2024 as new government settled in

---

## 10. KEY FINDINGS & STRATEGIC IMPLICATIONS

### 10.1 Concentration of Power

**The 2% Rule:**
- Just **2% of donors** (427 whales) control **69.7% of all political funding**
- **Grassroots donors** (12,556 small donors) contribute only **2.9%**

### 10.2 Ministerial Access Patterns

**Top Access Organizations:**
- CBI: 482 meetings across 16 departments (broadest reach)
- FSB: 462 meetings, 80 ministers
- Energy companies: BP (251), Shell (189), National Grid (200)
- Trade unions: Unite (214), UNISON (167)

### 10.3 The Full Influence Strategy

**48 organizations** use all three influence channels:
1. **Professional lobbying** (paying PR/lobbying agencies)
2. **Political donations** (funding parties/MPs)
3. **Ministerial meetings** (direct access to ministers)

Trade unions are the primary practitioners of this "full spectrum" approach.

### 10.4 Data Quality Improvements

After cleanup:
- Concatenated names split into proper entities
- Duplicate records merged
- Entity types corrected (Person vs Organization)
- 23,828 organizations matched to Companies House
- 62,747 director memberships imported
- 9,014 beneficial owner records added

---

## 11. DATA QUALITY

### 11.1 Strengths
- ✅ Comprehensive donation records: 91,508 donations (£1.59B)
- ✅ Rich organizational data: 64,337 organizations
- ✅ Ministerial meetings: 41,362 meetings with 119,793 attendees
- ✅ Lobbying integration: 62,798 consultancy relationships
- ✅ Companies House enrichment: 23,828 organizations matched
- ✅ Director data: 62,747 director memberships
- ✅ Beneficial ownership: 9,014 PSC records
- ✅ Lobbying workforce: 12,547 employees tracked

### 11.2 Pending Review Queue

11,198 Companies House matches pending human review (0.85-0.89 confidence).

---

## CONCLUSION

The UK political influence system is characterized by:

1. **Extreme concentration** - 2% of donors control 70% of funding
2. **Multi-channel influence** - 48 orgs use lobbying + donations + meetings
3. **Extensive ministerial access** - 41,362 meetings with external organizations
4. **Trade association dominance** - CBI, FSB, IoD lead on ministerial access
5. **Trade union sophistication** - Unions master the "full influence" approach
6. **Energy sector prominence** - BP, Shell, National Grid all in top 20 for access
7. **Director networks** - 10,980 individuals direct multiple organizations, creating hidden influence links
8. **Election cycle dynamics** - Clear pre-election donation surge and Purdah effects visible in data
9. **Cross-department coordination** - Major banks and tech firms conduct "blitz" campaigns across 5+ departments
10. **Improved data quality** - Post-cleanup data with Companies House enrichment enables deeper analysis

---

## APPENDIX: SQL Analysis Files

This report was generated from the following analysis files:

| File | Description |
|------|-------------|
| `01_database_overview.sql` | Core database statistics |
| `02_donation_analysis.sql` | Donor concentration and whale analysis |
| `03_ministerial_influence.sql` | Department and minister meeting patterns |
| `04_department_committee_analysis.sql` | Department-level analysis |
| `05_sector_analysis.sql` | Industry sector breakdown |
| `06_influence_triangle.sql` | Multi-channel influence analysis |
| `08_summary_stats.sql` | High-level summary statistics |
| `13_director_psc_analysis.sql` | Director and beneficial owner networks |
| `14_companies_house_progress.sql` | CH enrichment tracking |
| `15_advanced_insights.sql` | Cost of access, blitz campaigns, Lords nexus |
| `16_politician_profiles.sql` | Individual politician deep dives |
| `17_zack_polanski_deep_dive.sql` | Case study example |

---

**Report Generated By:** SQL Analysis Suite v6.0 (Post-Cleanup + Director Networks)
**Date:** 2026-01-25
**Database:** undertheinfluence (PostgreSQL 15)
**Data Sources:** Electoral Commission, GOV.UK Ministerial Meetings, APPC Register, Companies House
