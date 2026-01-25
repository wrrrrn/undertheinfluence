"""
Data Cleanup Utilities for UnderTheInfluence.

This module is the SINGLE SOURCE OF TRUTH for:
- Organization type detection patterns
- Person vs Organization classification
- Name splitting for concatenated entries
- Event description parsing

Used by:
- clean_data.py (cleanup orchestrator)
- entity_matcher.py (import-time entity resolution)
- import_ministerial_meetings.py (ingestion pipeline)
- populate_meeting_attendees.py (attendee splitting)
- populate_canonical.py (entity resolution bootstrap)

Phase 3.2 Implementation - Comprehensive Data Cleanup & Ingestion Fix
"""

import re
from typing import List, Optional, Tuple, Literal


class OrganizationPatterns:
    """
    Single source of truth for organization type detection patterns.

    Used to identify organizations that are NOT registrable with Companies House,
    such as government departments, councils, universities, etc.
    """

    ORG_TYPE_PATTERNS = {
        'government_dept': [
            r'\bdepartment\b', r'\bministry\b', r'\bcabinet office\b', r'\btreasury\b',
            r'\bhm government\b', r'\bdefra\b', r'\bdhsc\b', r'\bdfe\b', r'\bdwp\b',
            r'\bmoj\b', r'\bfco\b', r'\bfcdo\b', r'\bmod\b', r'\bhome office\b',
            r'\bdsit\b', r'\bdft\b', r'\bdbeis\b', r'\bbeis\b',
        ],
        'local_authority': [
            r'\bcouncil\b', r'\bborough\b', r'\bcity of\b', r'\blocal authority\b',
            r'\bmetropolitan\b', r'\bcounty\b',
        ],
        'university': [
            r'\buniversity\b', r'\bcollege\b', r'\bschool of\b', r'\bacademy\b',
            r'\bimperial college\b', r'\blse\b', r'\bucl\b', r'\boxford\b', r'\bcambridge\b',
        ],
        'nhs': [
            r'\bnhs\b', r'\bhospital\b', r'\bhealth trust\b', r'\bclinical commissioning\b',
            r'\bintegrated care\b', r'\bambulance\b', r'\bmental health\b',
        ],
        'police': [
            r'\bpolice\b', r'\bconstabulary\b',
        ],
        'trade_union': [
            r'\bunion\b(?!.*credit)', r'\btuc\b', r'\bunite\b', r'\bunison\b', r'\bgmb\b',
            r'\bnasuwt\b', r'\bneu\b', r'\brmt\b', r'\bpcs\b', r'\bfdh\b',
        ],
        'trade_body': [
            r'\bassociation\b', r'\bfederation\b', r'\binstitute\b(?!.*ltd)',
            r'\bsociety\b', r'\balliance\b', r'\bcoalition\b', r'\bcharity\b',
            r'\bfoundation\b', r'\btrust\b(?!.*limited)', r'\bcampaign\b',
        ],
        'foreign_entity': [
            r'\bgovernment of\b',
            r'\b(us|usa|american|french|german|chinese|indian|japanese)\s+(government|embassy|state)\b',
            r'\binc\.\s*$', r'\b(gmbh|ag|sa|bv|nv)\b',
        ],
        'embassy': [
            r'\bembassy\b', r'\bconsulate\b', r'\bhigh commission\b',
        ],
        'parliamentary': [
            r'\bappg\b', r'\ball[- ]party\b', r'\bparliamentary\b', r'\bcommons\b',
            r'\blords\b', r'\bwestminster\b', r'\bni assembly\b', r'\bwelsh assembly\b',
            r'\bscottish parliament\b', r'\bselect committee\b', r'\bsenedd\b',
        ],
        'regulator': [
            r'\bofcom\b', r'\bofgem\b', r'\bofwat\b', r'\bofsted\b', r'\bcma\b',
            r'\bfca\b', r'\bpra\b', r'\bice\b', r'\bhse\b', r'\benvironment agency\b',
        ],
        'concatenated': [
            r'^.{200,}$',  # Very long names are likely concatenated
            r',.*,.*,',    # Multiple commas suggest list
        ],
    }

    @classmethod
    def match_org_type(cls, name: str) -> Optional[str]:
        """
        Match an organization name to a type based on patterns.

        Args:
            name: Organization name to classify

        Returns:
            Organization type (e.g., 'government_dept', 'university') or None
        """
        if not name:
            return None

        name_lower = name.lower()

        for org_type, patterns in cls.ORG_TYPE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, name_lower, re.IGNORECASE):
                    return org_type

        return None

    @classmethod
    def is_non_ch_registrable(cls, name: str) -> bool:
        """
        Check if an organization is NOT registrable with Companies House.

        Returns True for entities that won't be found in CH:
        - Government departments
        - Councils and local authorities
        - Universities
        - NHS trusts
        - Police forces
        - Trade unions
        - Foreign entities
        - etc.

        Args:
            name: Organization name to check

        Returns:
            True if the organization is NOT registrable with Companies House
        """
        return cls.match_org_type(name) is not None

    @classmethod
    def is_concatenated(cls, name: str) -> bool:
        """
        Check if a name appears to be concatenated (multiple orgs/people smashed together).

        Args:
            name: Name to check

        Returns:
            True if the name appears concatenated
        """
        if not name:
            return False

        # Check for explicit patterns
        if len(name) > 200:
            return True
        if name.count(',') >= 3:
            return True
        if ';' in name:
            return True

        # Check for CamelCase smashing (e.g., "CompanyLtdAnotherCompany")
        # Multiple uppercase letters following lowercase letters
        transitions = len(re.findall(r'[a-z][A-Z]', name))
        if transitions >= 2:
            return True

        return False


class ActorClassifier:
    """
    Determine whether a name represents a Person or Organization.

    Consolidates classification logic from:
    - entity_matcher.py._is_organization()
    - split_concatenated_attendees.py org_keywords
    """

    # Person title patterns - names with these are almost certainly people
    PERSON_TITLE_PATTERNS = [
        r'\bMP\b',                    # Member of Parliament
        r'^(Rt\.?\s*Hon\.?|Right\s*Honourable)\s+',  # Rt Hon prefix
        r'^(Sir|Dame)\s+',            # Knights/Dames
        r'^(Lord|Lady|Baron|Baroness|Viscount|Earl|Countess|Duke|Duchess)\s+',  # Peers
        r'^(Dr|Doctor|Prof|Professor)\s+',  # Academic titles
        r'^(Rev|Reverend|Father|Bishop|Archbishop)\s+',  # Religious titles
        r'^(Gen|General|Col|Colonel|Maj|Major|Capt|Captain|Lt|Lieutenant|Admiral)\s+',  # Military
        r'^(Cllr|Councillor|Cllrs?)\s+',  # Councillors
        r',\s*(MP|MEP|MSP|MLA|AM)\s*$',  # Post-nominal letters
        r'\s+(MP|MEP|MSP|MLA|AM)\s*$',   # Post-nominal with space
        r'\b(QC|KC|CBE|OBE|MBE)\s*$',    # Honours
    ]

    # Organization keywords - names containing these are likely organizations
    ORG_KEYWORDS = [
        # Legal entities
        'ltd', 'limited', 'plc', 'llc', 'inc', 'corp', 'corporation',
        'gmbh', 'ag', 'sa', 'nv', 'bv', 'pty',

        # Organization types
        'group', 'holdings', 'partners', 'partnership',
        'association', 'society', 'institute', 'foundation',
        'trust', 'charity', 'council', 'committee',
        'union', 'federation', 'alliance', 'coalition',
        'company', 'companies', 'firm',
        'organization', 'organisation',

        # Government/Public sector
        'department', 'ministry', 'authority', 'agency',
        'office', 'commission', 'board', 'service',

        # Business types
        'studio', 'studios', 'productions', 'media',
        'consulting', 'consultants', 'advisors', 'advisory',
        'capital', 'ventures', 'investments',

        # Educational/Research
        'university', 'college', 'school', 'academy',
        'research', 'laboratory', 'labs',

        # Industry specific
        'bank', 'banking', 'insurance', 'pharmaceuticals',
        'healthcare', 'technologies', 'solutions', 'systems',
    ]

    # Known organization names (short names that don't have org keywords)
    KNOWN_ORGS = {
        'bbc', 'itn', 'sky', 'netflix', 'amazon', 'google', 'facebook', 'meta',
        'microsoft', 'apple', 'bt', 'ee', 'o2', 'vodafone', 'three', 'virgin',
        'hsbc', 'barclays', 'natwest', 'santander', 'tesco', 'sainsbury',
        'asda', 'morrisons', 'lidl', 'aldi', 'waitrose', 'coop',
        'deliveroo', 'uber', 'airbnb', 'spotify', 'twitter', 'x',
        'the guardian', 'the times', 'the telegraph', 'the sun', 'the mirror',
        'daily mail', 'financial times', 'the economist', 'reuters', 'bloomberg',
        'bp', 'shell', 'exxon', 'chevron', 'total', 'eni',
    }

    @classmethod
    def classify(cls, name: str) -> Literal['person', 'organization', 'unknown']:
        """
        Classify a name as person, organization, or unknown.

        Args:
            name: Actor name to classify

        Returns:
            'person', 'organization', or 'unknown'
        """
        if not name:
            return 'unknown'

        # Check for person titles first (highest confidence)
        if cls.has_person_title(name):
            return 'person'

        # Check for organization patterns
        if cls._is_organization(name):
            return 'organization'

        # If it starts with "The " it's likely an organization
        if name.startswith('The '):
            return 'organization'

        # All caps acronyms are usually organizations
        if name.isupper() and len(name) >= 2 and ' ' not in name.strip():
            return 'organization'

        # Check for known organizations
        if name.lower() in cls.KNOWN_ORGS:
            return 'organization'

        # Contains "&" between words often indicates organization
        # But we need to be careful of law firms like "Smith & Jones"
        if ' & ' in name and len(name.split()) >= 3:
            return 'organization'

        # Default: assume it's a person
        # Most meeting attendees are individuals
        return 'unknown'

    # Words that when in a name indicate an organization, not a person
    ORG_FOLLOWING_TITLE = [
        'university', 'college', 'school', 'academy', 'institute',
        'council', 'committee', 'panel', 'board', 'commission',
        'hospital', 'trust', 'foundation', 'charity', 'society',
        'medical', 'mills', 'motors', 'electric', 'dynamics', 'nuclear',
        'projects', 'digital', 'energy', 'airways', 'airlines',
        'foods', 'products', 'services', 'systems', 'solutions',
        'watch', 'network', 'group', 'scheme', 'programme', 'program',
        'states of', 'ministry', 'department', 'office',
    ]

    @classmethod
    def has_person_title(cls, name: str) -> bool:
        """
        Check if a name contains a person title (MP, Lord, Sir, Dr, etc.).

        This method distinguishes between personal titles and organization names
        that happen to start with similar words. For example:
        - "Sir David Attenborough" -> True (person with title)
        - "General Mills" -> False (organization)
        - "Duke University" -> False (organization)
        - "General Medical Council" -> False (organization)

        Args:
            name: Name to check

        Returns:
            True if the name contains a person title (and is likely a person)
        """
        if not name:
            return False

        # First check if this looks like an organization despite having title-like words
        name_lower = name.lower()
        for org_word in cls.ORG_FOLLOWING_TITLE:
            if org_word in name_lower:
                return False

        # Check for organizational keywords (comprehensive check)
        if cls._is_organization(name):
            return False

        # Now check for person title patterns
        for pattern in cls.PERSON_TITLE_PATTERNS:
            if re.search(pattern, name, re.IGNORECASE):
                return True

        return False

    @classmethod
    def _is_organization(cls, name: str) -> bool:
        """
        Check if a name looks like an organization.

        Args:
            name: Name to check

        Returns:
            True if the name appears to be an organization
        """
        name_lower = name.lower()

        # Check for org keywords
        for keyword in cls.ORG_KEYWORDS:
            # Use word boundary matching
            if re.search(rf'\b{re.escape(keyword)}\b', name_lower):
                return True

        return False


class NameSplitter:
    """
    Unified splitting for concatenated names in various formats.

    Handles:
    - "Company Ltd Another Company" (corporate suffix followed by name)
    - "Org A; Org B; Org C" (semicolon separated)
    - "Org A and Org B" (and-separated with care for "Marks & Spencer")
    - "Org A / Org B" (slash-separated)
    - "Person (Role), Person (Role)" (comma-separated with roles)
    """

    # Pattern to match company names that might have been smashed together
    CONCAT_PATTERN = re.compile(
        r'^(.+?(?:Ltd|Limited|PLC|Inc|LLP)\.?)\s+([A-Z].+)$',
        re.IGNORECASE
    )

    # Patterns to exclude from splitting (valid continuation after corporate suffix)
    EXCLUDE_PATTERNS = [
        re.compile(r'Limited\s+(Partnership|Company|Liability)$', re.IGNORECASE),
        re.compile(r'Ltd\s+(T/?A|C/?o)\s+', re.IGNORECASE),
        re.compile(r'Limited\s+(T/?A|C/?o)\s+', re.IGNORECASE),
        re.compile(r'PLC\s+Ltd$', re.IGNORECASE),
        re.compile(r'(Ltd|Limited|PLC)\s+(Co|Company)$', re.IGNORECASE),
        re.compile(r'(Ltd|Limited|PLC)\s+(UK|USA|Europe|International|Holdings|Group)$', re.IGNORECASE),
        re.compile(r'Public\s+Limited\s+Company$', re.IGNORECASE),
    ]

    # Delimiters used in attendee lists (in order of preference)
    ATTENDEE_DELIMITERS = [';', ' / ', ' and ', ', ']

    # Words that should NOT trigger "and" splitting
    AMPERSAND_EXCEPTIONS = {
        'marks & spencer', 'marks and spencer',
        'procter & gamble', 'procter and gamble',
        'johnson & johnson', 'johnson and johnson',
        'ernst & young', 'ernst and young',
        'deloitte & touche', 'deloitte and touche',
        'price waterhouse', 'pricewaterhousecoopers', 'pwc',
        'black & decker', 'black and decker',
        'arm & hammer', 'arm and hammer',
        'dolce & gabbana', 'dolce and gabbana',
        'barnes & noble', 'barnes and noble',
        'smith & wesson', 'smith and wesson',
        'simon & schuster', 'simon and schuster',
        'bed bath & beyond', 'bed bath and beyond',
        'harley-davidson', 'harley davidson',
    }

    @classmethod
    def split_org_name(cls, name: str) -> List[str]:
        """
        Split a concatenated organization name into parts.

        Handles "Company Ltd Another Company" patterns.

        Args:
            name: Organization name to split

        Returns:
            List of organization names (may contain just the original if no split)
        """
        if not name:
            return []

        # Check for exclusion patterns first
        for pattern in cls.EXCLUDE_PATTERNS:
            if pattern.search(name):
                return [name]

        # Try to match the concatenation pattern
        match = cls.CONCAT_PATTERN.match(name)
        if match:
            first = match.group(1).strip()
            second = match.group(2).strip()

            # Validate the split
            if len(second) < 5:
                return [name]

            # Skip common non-split words
            skip_words = {'Co', 'Company', 'Partnership', 'Group', 'Holdings', 'UK', 'USA'}
            if second in skip_words:
                return [name]

            # Check for trading-as patterns
            if second.lower().startswith('t/a') or second.lower().startswith('ta '):
                return [name]

            # Don't split if they're the same (case-insensitive)
            if first.lower().replace(' ', '') == second.lower().replace(' ', ''):
                return [name]

            # Recursively split the second part
            results = [first]
            results.extend(cls.split_org_name(second))
            return results

        return [name]

    @classmethod
    def split_attendee_list(cls, name: str) -> List[str]:
        """
        Split an attendee list into individual names.

        Handles multiple delimiter types with care for edge cases.

        Args:
            name: Raw attendee string (may contain multiple names)

        Returns:
            List of individual attendee names
        """
        if not name:
            return []

        name = name.strip()

        # Detect delimiter
        delimiter = cls.detect_delimiter(name)

        if delimiter is None:
            # No delimiter found - return as single item
            return [name] if name else []

        # Split by detected delimiter
        if delimiter == ';':
            parts = name.split(';')
        elif delimiter == ' / ':
            parts = name.split(' / ')
        elif delimiter == ' and ':
            # Check for ampersand exceptions
            name_lower = name.lower()
            if any(exc in name_lower for exc in cls.AMPERSAND_EXCEPTIONS):
                return [name]
            parts = re.split(r'\s+and\s+', name, flags=re.IGNORECASE)
        elif delimiter == ', ':
            # Comma split - be careful not to split inside parentheses
            parts = cls._split_on_comma_outside_parens(name)
        else:
            parts = [name]

        # Clean up parts
        cleaned = []
        for part in parts:
            part = part.strip()
            # Remove leading/trailing punctuation
            part = re.sub(r'^[,;\s]+', '', part)
            part = re.sub(r'[,;\s]+$', '', part)
            if part:
                cleaned.append(part)

        return cleaned

    @classmethod
    def _split_on_comma_outside_parens(cls, name: str) -> List[str]:
        """
        Split on commas that are NOT inside parentheses.

        Args:
            name: String to split

        Returns:
            List of parts
        """
        parts = []
        current = []
        paren_depth = 0

        for char in name:
            if char == '(':
                paren_depth += 1
                current.append(char)
            elif char == ')':
                paren_depth = max(0, paren_depth - 1)
                current.append(char)
            elif char == ',' and paren_depth == 0:
                # Split here
                parts.append(''.join(current))
                current = []
            else:
                current.append(char)

        # Don't forget the last part
        if current:
            parts.append(''.join(current))

        return parts

    @classmethod
    def detect_delimiter(cls, name: str) -> Optional[str]:
        """
        Detect the delimiter used in an attendee list.

        Args:
            name: Raw string to analyze

        Returns:
            Detected delimiter or None
        """
        if not name:
            return None

        # First, check for commas OUTSIDE parentheses - these are the most reliable
        comma_outside_parens = cls._has_delimiter_outside_parens(name, ',')
        if comma_outside_parens:
            return ', '

        # Check in order of specificity (only if no comma outside parens)
        if ';' in name:
            return ';'
        if ' / ' in name:
            return ' / '

        # Check for " and " that's not part of a known name and not inside parens
        if ' and ' in name.lower():
            # Make sure it's not an exception
            name_lower = name.lower()
            if not any(exc in name_lower for exc in cls.AMPERSAND_EXCEPTIONS):
                # Also check it's not inside parentheses
                if cls._has_delimiter_outside_parens(name, ' and '):
                    return ' and '

        return None

    @classmethod
    def _has_delimiter_outside_parens(cls, name: str, delimiter: str) -> bool:
        """
        Check if a delimiter exists outside of parentheses.

        Args:
            name: String to check
            delimiter: Delimiter to look for

        Returns:
            True if delimiter found outside parentheses
        """
        paren_depth = 0
        i = 0
        delimiter_lower = delimiter.lower()
        name_lower = name.lower()

        while i < len(name):
            if name[i] == '(':
                paren_depth += 1
            elif name[i] == ')':
                paren_depth = max(0, paren_depth - 1)
            elif paren_depth == 0:
                # Check if delimiter starts here
                if name_lower[i:i+len(delimiter)] == delimiter_lower:
                    return True
            i += 1

        return False


class EventDescriptionParser:
    """
    Detect event descriptions and extract attendees where possible.

    Handles patterns like:
    - "Roundtable with Company A, Company B"
    - "Call with Eurostar CEO"
    - "Meeting to discuss AI policy"
    - "Breakfast with industry stakeholders"
    """

    EVENT_TYPE_PATTERNS = [
        r'^(Roundtable|Round\s+table)',
        r'^(Call|Phone\s+call|Video\s+call|Conference\s+call)',
        r'^(Meeting|Meetings)',
        r'^(Breakfast|Lunch|Dinner)',
        r'^(Briefing|Brief)',
        r'^(Reception|Event)',
        r'^(Discussion|Discussions)',
        r'^(Visit|Site\s+visit)',
        r'^(Workshop)',
        r'^(Conference|Summit)',
        r'^(Introduction|Introductory)',
        r'^(Engagement)',
        r'^(Webinar)',
        # Note: "Industry" and "Stakeholder" removed - too many false positives
        # (e.g., "Industry Parliamentary Trust" is a real org)
    ]

    # Compiled pattern for efficiency
    EVENT_PATTERN = re.compile(
        r'^(' + '|'.join(f'(?:{p})' for p in EVENT_TYPE_PATTERNS) + r')\s+'
        r'(with|to|on|for|hosted|about|re|regarding|concerning|discussing)',
        re.IGNORECASE
    )

    @classmethod
    def is_event_description(cls, name: str) -> bool:
        """
        Check if a name is actually an event description, not an organization.

        Args:
            name: Name to check

        Returns:
            True if this is an event description
        """
        if not name:
            return False

        # Check for explicit event patterns
        if cls.EVENT_PATTERN.match(name):
            return True

        # Check for generic patterns
        name_lower = name.lower()

        # Starts with common event words (require connector to avoid false positives)
        event_starters = [
            'roundtable ', 'round table ', 'call with ', 'meeting with ',
            'breakfast with ', 'lunch with ', 'dinner with ', 'visit to ',
            'briefing on ', 'discussion on ', 'reception for ', 'event on ',
            'introduction to ', 'introductory ', 'engagement with ',
            'webinar with ', 'workshop with ',
            # Note: "industry " and "stakeholder " removed - too many false positives
            # (e.g., "Industry Parliamentary Trust", "Stakeholder Capital" are real orgs)
        ]
        if any(name_lower.startswith(s) for s in event_starters):
            return True

        # Specific stakeholder/industry patterns that ARE events
        stakeholder_event_patterns = [
            'stakeholder roundtable', 'stakeholder reception', 'stakeholder meeting',
            'stakeholder engagement', 'stakeholder event',
            'industry roundtable', 'industry reception', 'industry meeting',
            'industry day', 'industry event',
        ]
        if any(name_lower.startswith(p) for p in stakeholder_event_patterns):
            return True

        return False

    @classmethod
    def extract_attendees(cls, event_description: str) -> List[str]:
        """
        Try to extract attendee names from an event description.

        Args:
            event_description: Event description string

        Returns:
            List of extracted attendee names (may be empty)
        """
        if not event_description:
            return []

        # Normalize: strip optional prefixes like "Introductory"
        normalized = re.sub(
            r'^(?:Introductory|Initial|Follow-up|Follow\s+up)\s+',
            '',
            event_description,
            flags=re.IGNORECASE
        ).strip()

        # Event types that can have attendees extracted
        event_types = (
            r'Roundtable|Round\s+table|Meeting|Meetings|Call|Phone\s+call|Video\s+call|'
            r'Breakfast|Lunch|Dinner|Briefing|Brief|'
            r'Reception|Event|Webinar|'
            r'Discussion|Discussions|Workshop|'
            r'Engagement|Conference|Summit'
        )

        # Connectors that link event type to attendees
        connectors = r'with|hosted\s+by|for|featuring'

        # Pattern: "[Event type] [connector] [attendees]"
        match = re.match(
            rf'^(?:{event_types})\s+(?:{connectors})\s+(.+)$',
            normalized,
            re.IGNORECASE
        )

        if match:
            attendees_str = match.group(1)
            # Split by comma or "and"
            return NameSplitter.split_attendee_list(attendees_str)

        # Pattern: "Call/Meeting with [Title] of [Organization]" - extract organization
        match = re.match(
            r'^(?:Call|Meeting|Breakfast|Lunch|Dinner)\s+with\s+'
            r'(?:the\s+)?(?:CEO|CFO|CTO|MD|Director|Head|President|Chair|Chairman)\s+'
            r'(?:of\s+)?(.+)$',
            normalized,
            re.IGNORECASE
        )

        if match:
            return [match.group(1)]

        # Could not extract specific attendees
        return []

    @classmethod
    def get_event_type(cls, event_description: str) -> Optional[str]:
        """
        Get the type of event from the description.

        Args:
            event_description: Event description string

        Returns:
            Event type (e.g., 'roundtable', 'meeting', 'call') or None
        """
        if not event_description:
            return None

        for pattern in cls.EVENT_TYPE_PATTERNS:
            match = re.match(pattern, event_description, re.IGNORECASE)
            if match:
                return match.group(1).lower().replace(' ', '_')

        return None


class NameNormalizer:
    """
    Name quality normalization utilities.

    Fixes:
    - Double spaces
    - Trailing punctuation
    - Inconsistent capitalization
    """

    # Threshold for treating whitespace as a column separator vs typo
    COLUMN_SEPARATOR_THRESHOLD = 6  # 6+ spaces = likely tabular data

    @classmethod
    def normalize(cls, name: str, fix_case: bool = False) -> str:
        """
        Normalize a name for consistency.

        Args:
            name: Name to normalize
            fix_case: If True, fix capitalization (risky - may break proper names)

        Returns:
            Normalized name
        """
        if not name:
            return ''

        # First, convert long whitespace runs to semicolons (likely tabular data)
        # "Company                    Person" -> "Company; Person"
        normalized = re.sub(
            rf'\s{{{cls.COLUMN_SEPARATOR_THRESHOLD},}}',
            '; ',
            name
        )

        # Then collapse remaining double/triple spaces to single space
        normalized = re.sub(r'  +', ' ', normalized)

        # Strip leading/trailing whitespace
        normalized = normalized.strip()

        # Remove trailing punctuation (except closing parenthesis)
        normalized = re.sub(r'[,;:]+$', '', normalized)

        # Remove leading punctuation
        normalized = re.sub(r'^[,;:\-]+\s*', '', normalized)

        # Fix double quotes/apostrophes
        normalized = re.sub(r'["""]', '"', normalized)
        normalized = re.sub(r"['''`]", "'", normalized)

        if fix_case:
            # Only fix obviously wrong cases (all lowercase, all uppercase)
            if normalized.islower() or normalized.isupper():
                normalized = normalized.title()

        return normalized

    @classmethod
    def has_quality_issues(cls, name: str) -> List[str]:
        """
        Check for name quality issues.

        Args:
            name: Name to check

        Returns:
            List of issue descriptions (empty if no issues)
        """
        issues = []

        if not name:
            return ['empty_name']

        # Check for tabular column separators (long whitespace runs) first
        if re.search(rf'\s{{{cls.COLUMN_SEPARATOR_THRESHOLD},}}', name):
            issues.append('tabular_columns')
        elif '  ' in name:
            # Only flag as double_spaces if not tabular
            issues.append('double_spaces')

        if name != name.strip():
            issues.append('leading_trailing_whitespace')

        if re.search(r'[,;:]+$', name):
            issues.append('trailing_punctuation')

        if re.search(r'^[,;:\-]+\s*', name):
            issues.append('leading_punctuation')

        # Check for lowercase start (excluding known lowercase brands)
        LOWERCASE_EXCEPTIONS = {'eBay', 'iPhone', 'iPad', 'iPlayer', 'eMoney'}
        if name and name[0].islower() and name not in LOWERCASE_EXCEPTIONS:
            # Only flag if it's not a known lowercase brand
            if not any(name.startswith(exc) for exc in LOWERCASE_EXCEPTIONS):
                issues.append('lowercase_start')

        return issues


class CamelCaseSplitter:
    """
    Split CamelCase smashed names with no delimiter.

    Example: "Wildlife and Countryside LinkNorth Yorkshire Moors"
    """

    # Legitimate CamelCase company/brand names that should NOT be split
    CAMELCASE_EXCEPTIONS = {
        'glaxosmithkline', 'smithkline', 'beecham',
        'pricewaterhousecoopers', 'pricewaterhouse',
        'daimlerchrysler',
        'comcast',
        'mastercard', 'eurocard',
        'wellcome',  # Burroughs Wellcome
        'youtube',
        'linkedin',
        'whatsapp',
        'wordpress',
        'javascript', 'typescript', 'coffeescript',
        'github', 'gitlab', 'bitbucket',
        'stackoverflow',
        'paypal',
        'fedex',
        'adidas',
        'volkswagen',
        'dreamworks',
        'salesforce',
        'mailchimp',
        'hubspot',
        'shopify',
        'squarespace',
        'wework',
        'airbus',
        'raytheon',
        'lockheed',
        'northrop',
        'textron',
        'honeywell',
        'rockwell',
        'easyjet',
        'ryanair',
        'jetblue',
        'southwest',
        # Pharmaceutical companies
        'abbvie', 'astrazeneca', 'novartis', 'sanofi', 'bayer',
        'boehringer', 'gilead', 'merck', 'pfizer', 'roche',
        'biomerieux', 'biomarin',
        # Tech companies
        'actionfunder', 'healthtech', 'fintech', 'biotech', 'cleantech',
        'medtech', 'edtech', 'agritech', 'proptech', 'insurtech',
        'qinetiq', 'eleclink', 'zeroavia', 'cyprusone', 'tenu',
        'loftzone', 'hydrab', 'tiktok',
        # Investment/Financial
        'blackrock', 'vanguard', 'fidelity', 'statestreet',
        'natwest',
        # Other brands with internal caps
        'energyuk', 'networkrail', 'nationalrail',
        'thecityuk', 'techuk', 'openrights', 'openrightsgroup',
        'serviceow', 'cityfibre', 'insta', 'instadeep',
    }

    @classmethod
    def detect_camelcase_transitions(cls, name: str) -> List[int]:
        """
        Find positions where CamelCase transitions occur.

        Args:
            name: Name to analyze

        Returns:
            List of positions where lowercase→uppercase transitions occur
        """
        positions = []
        for i in range(1, len(name)):
            if name[i-1].islower() and name[i].isupper():
                positions.append(i)
        return positions

    @classmethod
    def should_split(cls, name: str) -> bool:
        """
        Determine if a name should be split based on CamelCase patterns.

        Args:
            name: Name to check

        Returns:
            True if the name appears to be multiple names smashed together
        """
        if not name:
            return False

        # Check if the name contains any known CamelCase exceptions
        # Only match if the exception appears as part of a CamelCase word
        # (not just anywhere in the string as a substring)
        name_lower = name.lower()
        import re
        for exception in cls.CAMELCASE_EXCEPTIONS:
            # Check if exception appears at a CamelCase boundary
            # e.g., "AbbVie" should match, but "HealthTech Industries" should not block splitting
            # because "HealthTech" is followed by a space, not smashed together
            if exception in name_lower:
                # Find where it occurs
                pos = name_lower.find(exception)
                # If it's at a word boundary (followed by space or end), don't count it
                end_pos = pos + len(exception)
                if end_pos >= len(name) or name[end_pos] == ' ':
                    continue  # This is a normal word, not a CamelCase smash
                # If followed by uppercase (CamelCase continuation), this is an exception
                if end_pos < len(name) and name[end_pos].isupper():
                    return False

        # Get all transitions
        transitions = cls.detect_camelcase_transitions(name)
        if len(transitions) < 1:
            return False

        # Count valid (non-exception) transitions
        valid_transitions = 0
        for pos in transitions:
            # Check for common patterns that shouldn't be split
            before = name[max(0, pos-3):pos]

            # Irish/Scottish names - skip these transitions
            if before.lower().endswith('mc') or before.lower().endswith('mac'):
                continue
            if before.lower().endswith("o'"):
                continue

            # Single lowercase letter prefixes (iPhone, eBay, etc.) - skip
            if pos <= 2 and name[:pos].islower():
                continue

            # This is a valid concatenation transition
            valid_transitions += 1

        # Need at least 1 valid transition
        return valid_transitions >= 1

    @classmethod
    def _is_exception_at_position(cls, name: str, pos: int) -> bool:
        """
        Check if position is part of a known CamelCase exception word.

        Args:
            name: The full name string
            pos: Position of a CamelCase transition

        Returns:
            True if this position is inside a known exception word
        """
        name_lower = name.lower()
        for exception in cls.CAMELCASE_EXCEPTIONS:
            # Find all occurrences of this exception
            start = 0
            while True:
                idx = name_lower.find(exception, start)
                if idx == -1:
                    break
                # Check if the transition position is within this exception
                if idx < pos <= idx + len(exception):
                    return True
                start = idx + 1
        return False

    @classmethod
    def split(cls, name: str) -> List[str]:
        """
        Split a CamelCase smashed name into parts.

        Args:
            name: Name to split

        Returns:
            List of split parts
        """
        if not cls.should_split(name):
            return [name]

        transitions = cls.detect_camelcase_transitions(name)

        # Build parts
        parts = []
        start = 0

        for pos in transitions:
            # Check for patterns we shouldn't split on
            before = name[max(0, pos-3):pos]
            if before.lower().endswith('mc') or before.lower().endswith('mac'):
                continue
            if before.lower().endswith("o'"):
                continue

            # Check if this position is inside a known CamelCase exception
            if cls._is_exception_at_position(name, pos):
                continue

            part = name[start:pos].strip()
            if part:
                parts.append(part)
            start = pos

        # Add the last part
        if start < len(name):
            part = name[start:].strip()
            if part:
                parts.append(part)

        # If we only got one part, splitting failed
        if len(parts) <= 1:
            return [name]

        return parts
