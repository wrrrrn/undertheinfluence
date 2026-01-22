"""
UK Government Department Configuration for Ministerial Meetings Import

This module defines all current and historical government departments
with their GOV.UK collection URLs for ministerial transparency data.

Last updated: January 2026
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class DepartmentConfig:
    """Configuration for a UK government department."""
    name: str  # Full official name
    short_name: str  # Abbreviation (e.g., "DSIT", "DfT")
    slug: str  # URL-safe slug
    collection_url: str  # GOV.UK collection page URL
    start_date: Optional[str] = None  # When department was created (YYYY-MM-DD)
    end_date: Optional[str] = None  # When department was abolished (YYYY-MM-DD)
    predecessor: Optional[str] = None  # Short name of predecessor department
    notes: str = ""


# Current Government Departments (as of January 2026)
# Organized alphabetically by short name

DEPARTMENTS = {
    'AGO': DepartmentConfig(
        name="Attorney General's Office",
        short_name="AGO",
        slug="attorney-generals-office",
        collection_url="",  # No collection page - individual quarterly publications
        start_date="1277-01-01",  # Historical office
        notes="Legal advisor to the government. Quarterly returns from 2011+. Search for 'AGO ministerial transparency returns'"
    ),

    'CO': DepartmentConfig(
        name="Cabinet Office",
        short_name="CO",
        slug="cabinet-office",
        collection_url="https://www.gov.uk/government/collections/ministers-transparency-publications",
        start_date="1916-12-09",
        notes="Supports the Prime Minister and Cabinet. Includes Leader of Commons and Leader of Lords."
    ),

    'DBT': DepartmentConfig(
        name="Department for Business and Trade",
        short_name="DBT",
        slug="department-for-business-and-trade",
        collection_url="https://www.gov.uk/government/collections/dbt-ministers-transparency-publications",
        start_date="2023-02-07",
        predecessor="BEIS",
        notes="Created from BEIS and DIT merger"
    ),

    'DCMS': DepartmentConfig(
        name="Department for Culture, Media and Sport",
        short_name="DCMS",
        slug="department-for-culture-media-and-sport",
        collection_url="",  # No collection page - individual quarterly publications
        start_date="1992-04-01",
        notes="No collection page post-2013. Search for quarterly publications individually."
    ),

    'Defra': DepartmentConfig(
        name="Department for Environment, Food and Rural Affairs",
        short_name="Defra",
        slug="department-for-environment-food-and-rural-affairs",
        collection_url="https://www.gov.uk/government/collections/ministers-hospitality-gifts-meetings-overseas-travel",
        start_date="2001-06-08",
        notes="Environment, farming, food production, animal welfare"
    ),

    'DESNZ': DepartmentConfig(
        name="Department for Energy Security and Net Zero",
        short_name="DESNZ",
        slug="department-for-energy-security-and-net-zero",
        collection_url="https://www.gov.uk/government/collections/desnz-ministerial-gifts-hospitality-travel-and-meetings",
        start_date="2023-02-07",
        predecessor="BEIS",
        notes="Energy policy and net zero transition"
    ),

    'MHCLG': DepartmentConfig(
        name="Ministry of Housing, Communities and Local Government",
        short_name="MHCLG",
        slug="ministry-of-housing-communities-and-local-government",
        collection_url="https://www.gov.uk/government/collections/dclg-ministerial-data",
        start_date="2024-07-01",  # Renamed from DLUHC July 2024
        predecessor="DLUHC",
        notes="Renamed from DLUHC July 2024. Same collection URL covers all names: DCLG->MHCLG->DLUHC->MHCLG. Data from 2010."
    ),

    'DSIT': DepartmentConfig(
        name="Department for Science, Innovation and Technology",
        short_name="DSIT",
        slug="department-for-science-innovation-and-technology",
        collection_url="https://www.gov.uk/government/collections/dsit-ministerial-gifts-hospitality-travel-and-meetings",
        start_date="2023-02-07",
        predecessor="BEIS",
        notes="Science, research, innovation, digital, telecoms"
    ),

    'DfE': DepartmentConfig(
        name="Department for Education",
        short_name="DfE",
        slug="department-for-education",
        collection_url="https://www.gov.uk/government/collections/dfe-ministers-quarterly-returns",
        start_date="1992-07-01",
        notes="Education policy and children's services. One of the most complete historical records from May 2010."
    ),

    'DfT': DepartmentConfig(
        name="Department for Transport",
        short_name="DfT",
        slug="department-for-transport",
        collection_url="https://www.gov.uk/government/collections/dft-ministerial-gifts-hospitality-travel-and-meetings",
        start_date="2002-05-29",
        notes="Transport policy and infrastructure. Historical data from 2009."
    ),

    'DHSC': DepartmentConfig(
        name="Department of Health and Social Care",
        short_name="DHSC",
        slug="department-of-health-and-social-care",
        collection_url="https://www.gov.uk/government/collections/ministerial-gifts-hospitality-overseas-travel-and-meetings",
        start_date="2018-01-08",
        predecessor="DH",
        notes="Renamed from Department of Health in 2018. Data from Q1 2012 onwards."
    ),

    'DWP': DepartmentConfig(
        name="Department for Work and Pensions",
        short_name="DWP",
        slug="department-for-work-and-pensions",
        collection_url="https://www.gov.uk/government/collections/dwp-ministers-hospitality-and-gifts",
        start_date="2001-06-08",
        notes="Exceptionally comprehensive data from Q3 2010 onwards. Most complete historical record."
    ),

    'FCDO': DepartmentConfig(
        name="Foreign, Commonwealth and Development Office",
        short_name="FCDO",
        slug="foreign-commonwealth-development-office",
        collection_url="https://www.gov.uk/government/collections/fcdo-ministerial-travel-and-meetings",
        start_date="2020-09-02",
        predecessor="FCO",
        notes="Merger of FCO and DFID in 2020. Current collection from Oct 2024."
    ),

    'HMT': DepartmentConfig(
        name="HM Treasury",
        short_name="HMT",
        slug="hm-treasury",
        collection_url="https://www.gov.uk/government/collections/hm-treasury-ministerial-overseas-travel-and-meetings",
        start_date="1714-01-01",  # Historical
        notes="Current collection from Oct 2024. Historical: https://www.gov.uk/government/collections/hmt-ministers-meetings-hospitality-gifts-and-overseas-travel"
    ),

    'HO': DepartmentConfig(
        name="Home Office",
        short_name="HO",
        slug="home-office",
        collection_url="https://www.gov.uk/government/collections/home-office-ministers-hospitality-data",
        start_date="1782-03-27",  # Historical
        notes="Immigration, security, policing, counter-terrorism. Data from Q2 2013 onwards."
    ),

    'MoD': DepartmentConfig(
        name="Ministry of Defence",
        short_name="MoD",
        slug="ministry-of-defence",
        collection_url="https://www.gov.uk/government/collections/ministerial-gifts-hospitality-travel-and-meetings-with-external-organisations-in-the-ministry-of-defence",
        start_date="1964-04-01",
        notes="Historical collection 2010-2024. New collection from Oct 2024: https://www.gov.uk/government/collections/mod-ministerial-overseas-travel-and-meetings"
    ),

    'MoJ': DepartmentConfig(
        name="Ministry of Justice",
        short_name="MoJ",
        slug="ministry-of-justice",
        collection_url="https://www.gov.uk/government/collections/moj-gifts-hospitality-travel-and-meetings",
        start_date="2007-05-09",
        notes="Courts, prisons, probation, legal aid. Data from Q1 2011 onwards."
    ),

    'NIO': DepartmentConfig(
        name="Northern Ireland Office",
        short_name="NIO",
        slug="northern-ireland-office",
        collection_url="https://www.gov.uk/government/collections/nio-ministerial-gifts-hospitality-travel-and-meetings-data-collection",
        start_date="1972-03-30",
        notes="Quarterly transparency data from 2021 onwards"
    ),

    'OAG': DepartmentConfig(
        name="Office of the Advocate General for Scotland",
        short_name="OAG",
        slug="office-of-the-advocate-general-for-scotland",
        collection_url="",  # No collection page - individual quarterly publications
        start_date="1999-07-01",
        notes="Legal advisor on Scottish law. Quarterly returns from 2021+. Search for 'OAG ministerial gifts hospitality travel meetings'"
    ),

    'SO': DepartmentConfig(
        name="Scotland Office",
        short_name="SO",
        slug="scotland-office",
        collection_url="",  # No collection page - individual quarterly publications
        start_date="1999-07-01",
        notes="UK government in Scotland. Search for 'Scotland Office: ministerial transparency return'"
    ),

    'WO': DepartmentConfig(
        name="Wales Office",
        short_name="WO",
        slug="wales-office",
        collection_url="https://www.gov.uk/government/collections/office-of-the-secretary-of-state-for-wales-data-gifts-hospitality-travel-and-meetings",
        start_date="1999-07-01",
        notes="UK government in Wales. Includes special advisers data. Coverage from 2020."
    ),

    'UKEF': DepartmentConfig(
        name="UK Export Finance",
        short_name="UKEF",
        slug="uk-export-finance",
        collection_url="https://www.gov.uk/government/collections/ukef-ministers-meetings-hospitality-gifts-and-overseas-travel",
        start_date="1919-01-01",  # Historical (as Export Credits Guarantee Department)
        notes="Export credit agency. Quarterly transparency data."
    ),

    # Historical Departments (abolished but have historical data)

    'BEIS': DepartmentConfig(
        name="Department for Business, Energy and Industrial Strategy",
        short_name="BEIS",
        slug="department-for-business-energy-and-industrial-strategy",
        collection_url="https://www.gov.uk/government/collections/beis-ministerial-gifts-hospitality-travel-and-meetings",
        start_date="2016-07-14",
        end_date="2023-02-07",
        predecessor="BIS",
        notes="Abolished Feb 2023, split into DSIT, DBT, DESNZ. Coverage July 2016 - Jan 2023."
    ),

    'BIS': DepartmentConfig(
        name="Department for Business, Innovation and Skills",
        short_name="BIS",
        slug="department-for-business-innovation-and-skills",
        collection_url="https://www.gov.uk/government/collections/bis-quarterly-publications-april-to-june-2012",
        start_date="2009-06-05",
        end_date="2016-07-14",
        notes="Merged with DECC to form BEIS. Coverage 2012 - June 2016."
    ),

    'DECC': DepartmentConfig(
        name="Department of Energy and Climate Change",
        short_name="DECC",
        slug="department-of-energy-and-climate-change",
        collection_url="https://www.gov.uk/government/collections/decc-ministerial-gifts-hospitality-meetings-and-travel",
        start_date="2008-10-03",
        end_date="2016-07-14",
        notes="Merged with BIS to form BEIS. Main collection 2015-2016. Earlier data in separate collections."
    ),

    'DFID': DepartmentConfig(
        name="Department for International Development",
        short_name="DFID",
        slug="department-for-international-development",
        collection_url="https://www.gov.uk/government/collections/dfid-ministerial-gifts-hospitality-travel-and-meetings",
        start_date="1997-05-01",
        end_date="2020-09-02",
        notes="Merged with FCO to form FCDO. Coverage 2010 - Sept 2020."
    ),

    'DIT': DepartmentConfig(
        name="Department for International Trade",
        short_name="DIT",
        slug="department-for-international-trade",
        collection_url="https://www.gov.uk/government/collections/dit-ministerial-gifts-hospitality-travel-and-meetings",
        start_date="2016-07-14",
        end_date="2023-02-07",
        notes="Merged with parts of BEIS to form DBT. Coverage July 2016 - Feb 2023."
    ),

    'FCO': DepartmentConfig(
        name="Foreign and Commonwealth Office",
        short_name="FCO",
        slug="foreign-commonwealth-office",
        collection_url="https://www.gov.uk/government/collections/minister-data",
        start_date="1968-10-17",
        end_date="2020-09-02",
        notes="Merged with DFID to form FCDO. Coverage 2013 - Sept 2020."
    ),

    'DLUHC': DepartmentConfig(
        name="Department for Levelling Up, Housing and Communities",
        short_name="DLUHC",
        slug="department-for-levelling-up-housing-and-communities",
        collection_url="https://www.gov.uk/government/collections/dclg-ministerial-data",
        start_date="2021-09-15",
        end_date="2024-07-01",
        predecessor="MHCLG",
        notes="Renamed to MHCLG July 2024. Same collection URL. Coverage Sept 2021 - July 2024."
    ),
}


def get_active_departments(as_of_date: str = None) -> dict:
    """
    Get departments that were active on a given date.

    Args:
        as_of_date: ISO date string (YYYY-MM-DD). If None, returns current departments.

    Returns:
        Dictionary of active departments on that date
    """
    if as_of_date is None:
        # Return departments with no end_date (currently active)
        return {k: v for k, v in DEPARTMENTS.items() if v.end_date is None}

    # Filter by date range
    active = {}
    for short_name, dept in DEPARTMENTS.items():
        started = dept.start_date is None or dept.start_date <= as_of_date
        not_ended = dept.end_date is None or dept.end_date > as_of_date

        if started and not_ended:
            active[short_name] = dept

    return active


def get_department_by_name(name: str) -> Optional[DepartmentConfig]:
    """
    Get department config by any name variant (full name, short name, or slug).

    Args:
        name: Department name in any format

    Returns:
        DepartmentConfig if found, None otherwise
    """
    name_lower = name.lower()

    # Try exact match on short name
    if name in DEPARTMENTS:
        return DEPARTMENTS[name]

    # Try case-insensitive match on short name
    for short_name, dept in DEPARTMENTS.items():
        if short_name.lower() == name_lower:
            return dept

    # Try match on full name
    for dept in DEPARTMENTS.values():
        if dept.name.lower() == name_lower:
            return dept

    # Try match on slug
    for dept in DEPARTMENTS.values():
        if dept.slug.lower() == name_lower:
            return dept

    return None


def get_department_successors(short_name: str) -> list:
    """
    Get departments that succeeded this department.

    Args:
        short_name: Department short name (e.g., "BEIS")

    Returns:
        List of DepartmentConfig objects that list this as predecessor
    """
    successors = []
    for dept in DEPARTMENTS.values():
        if dept.predecessor == short_name:
            successors.append(dept)
    return successors
