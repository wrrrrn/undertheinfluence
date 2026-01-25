"""
Unit tests for datafetch/utils/data_cleanup.py

Tests the shared utility module with:
- OrganizationPatterns - org type detection
- ActorClassifier - person vs organization classification
- NameSplitter - splitting concatenated names
- EventDescriptionParser - detecting/parsing event descriptions
- NameNormalizer - name quality fixes
- CamelCaseSplitter - splitting CamelCase names
"""

import pytest

from datafetch.utils.data_cleanup import (
    OrganizationPatterns,
    ActorClassifier,
    NameSplitter,
    EventDescriptionParser,
    NameNormalizer,
    CamelCaseSplitter,
)


class TestOrganizationPatterns:
    """Tests for OrganizationPatterns class."""

    def test_match_org_type_government(self):
        """Government departments should be identified."""
        assert OrganizationPatterns.match_org_type("Department for Education") == "government_dept"
        assert OrganizationPatterns.match_org_type("Ministry of Defence") == "government_dept"
        assert OrganizationPatterns.match_org_type("HM Treasury") == "government_dept"
        assert OrganizationPatterns.match_org_type("Home Office") == "government_dept"
        assert OrganizationPatterns.match_org_type("DSIT") == "government_dept"

    def test_match_org_type_local_authority(self):
        """Local authorities should be identified."""
        assert OrganizationPatterns.match_org_type("Bristol City Council") == "local_authority"
        assert OrganizationPatterns.match_org_type("London Borough of Camden") == "local_authority"
        assert OrganizationPatterns.match_org_type("Derbyshire County Council") == "local_authority"

    def test_match_org_type_university(self):
        """Universities should be identified."""
        assert OrganizationPatterns.match_org_type("University of Oxford") == "university"
        assert OrganizationPatterns.match_org_type("Imperial College London") == "university"
        assert OrganizationPatterns.match_org_type("London School of Economics") == "university"

    def test_match_org_type_nhs(self):
        """NHS organizations should be identified."""
        assert OrganizationPatterns.match_org_type("NHS England") == "nhs"
        assert OrganizationPatterns.match_org_type("Royal Brompton Hospital") == "nhs"
        assert OrganizationPatterns.match_org_type("Clinical Commissioning Group") == "nhs"

    def test_match_org_type_trade_union(self):
        """Trade unions should be identified."""
        assert OrganizationPatterns.match_org_type("Unite the Union") == "trade_union"
        assert OrganizationPatterns.match_org_type("TUC") == "trade_union"
        assert OrganizationPatterns.match_org_type("UNISON") == "trade_union"
        assert OrganizationPatterns.match_org_type("GMB") == "trade_union"

    def test_match_org_type_none_for_companies(self):
        """Regular companies should not match any org type."""
        assert OrganizationPatterns.match_org_type("Acme Corporation Ltd") is None
        assert OrganizationPatterns.match_org_type("Google UK") is None
        assert OrganizationPatterns.match_org_type("British Airways PLC") is None

    def test_is_non_ch_registrable_true(self):
        """Non-CH registrable orgs should return True."""
        assert OrganizationPatterns.is_non_ch_registrable("Bristol City Council") is True
        assert OrganizationPatterns.is_non_ch_registrable("Department for Education") is True
        assert OrganizationPatterns.is_non_ch_registrable("University of Cambridge") is True

    def test_is_non_ch_registrable_false(self):
        """CH registrable orgs should return False."""
        assert OrganizationPatterns.is_non_ch_registrable("Acme Ltd") is False
        assert OrganizationPatterns.is_non_ch_registrable("Google UK Limited") is False

    def test_is_concatenated_long_name(self):
        """Very long names should be detected as concatenated."""
        long_name = "A" * 250
        assert OrganizationPatterns.is_concatenated(long_name) is True

    def test_is_concatenated_multiple_commas(self):
        """Names with many commas should be detected as concatenated."""
        assert OrganizationPatterns.is_concatenated("A, B, C, D") is True

    def test_is_concatenated_semicolon(self):
        """Names with semicolons should be detected as concatenated."""
        assert OrganizationPatterns.is_concatenated("Org A; Org B") is True

    def test_is_concatenated_normal_name(self):
        """Normal names should not be detected as concatenated."""
        assert OrganizationPatterns.is_concatenated("Acme Corporation Ltd") is False


class TestActorClassifier:
    """Tests for ActorClassifier class."""

    def test_classify_person_mp(self):
        """MPs should be classified as persons."""
        assert ActorClassifier.classify("Aaron Bell MP") == "person"
        assert ActorClassifier.classify("John Smith, MP") == "person"
        assert ActorClassifier.classify("Jane Doe MEP") == "person"

    def test_classify_person_titled(self):
        """Titled individuals should be classified as persons."""
        assert ActorClassifier.classify("Sir David Attenborough") == "person"
        assert ActorClassifier.classify("Lord Frost") == "person"
        assert ActorClassifier.classify("Dame Judi Dench") == "person"
        assert ActorClassifier.classify("Dr Sarah Gilbert") == "person"
        assert ActorClassifier.classify("Professor Stephen Hawking") == "person"

    def test_classify_person_rt_hon(self):
        """Rt Hon title should indicate person."""
        assert ActorClassifier.classify("Rt Hon Rishi Sunak") == "person"
        assert ActorClassifier.classify("Right Honourable Keir Starmer") == "person"

    def test_classify_organization_legal_suffix(self):
        """Organizations with legal suffixes should be classified correctly."""
        assert ActorClassifier.classify("Acme Corporation Ltd") == "organization"
        assert ActorClassifier.classify("British Airways PLC") == "organization"
        assert ActorClassifier.classify("McKinsey & Company Inc") == "organization"

    def test_classify_organization_keywords(self):
        """Organizations with org keywords should be classified correctly."""
        assert ActorClassifier.classify("National Grid Group") == "organization"
        assert ActorClassifier.classify("British Medical Association") == "organization"
        assert ActorClassifier.classify("Royal Society Foundation") == "organization"

    def test_classify_organization_the_prefix(self):
        """Organizations starting with 'The' should be classified correctly."""
        assert ActorClassifier.classify("The Guardian") == "organization"
        assert ActorClassifier.classify("The Times") == "organization"

    def test_classify_organization_acronym(self):
        """All-caps acronyms should be classified as organizations."""
        assert ActorClassifier.classify("BBC") == "organization"
        assert ActorClassifier.classify("HSBC") == "organization"

    def test_classify_unknown_for_ambiguous(self):
        """Ambiguous names should return unknown."""
        assert ActorClassifier.classify("John Smith") == "unknown"
        assert ActorClassifier.classify("Sarah Jones") == "unknown"

    def test_has_person_title_true(self):
        """Names with titles should return True."""
        assert ActorClassifier.has_person_title("Aaron Bell MP") is True
        assert ActorClassifier.has_person_title("Sir Alan Sugar") is True
        assert ActorClassifier.has_person_title("Dr Jane Smith") is True
        assert ActorClassifier.has_person_title("Prof John Doe") is True

    def test_has_person_title_false(self):
        """Names without titles should return False."""
        assert ActorClassifier.has_person_title("Acme Ltd") is False
        assert ActorClassifier.has_person_title("John Smith") is False


class TestNameSplitter:
    """Tests for NameSplitter class."""

    def test_split_org_name_concatenated(self):
        """Concatenated org names should be split correctly."""
        result = NameSplitter.split_org_name("Company Ltd Another Company")
        assert len(result) == 2
        assert "Company Ltd" in result
        assert "Another Company" in result

    def test_split_org_name_multiple(self):
        """Multiple concatenations should be split recursively."""
        result = NameSplitter.split_org_name("First Ltd Second Ltd Third Company")
        assert len(result) == 3
        assert "First Ltd" in result
        assert "Second Ltd" in result
        assert "Third Company" in result

    def test_split_org_name_no_split_needed(self):
        """Normal org names should not be split."""
        result = NameSplitter.split_org_name("Acme Corporation Limited")
        assert result == ["Acme Corporation Limited"]

    def test_split_org_name_exclude_patterns(self):
        """Exclusion patterns should prevent splitting."""
        # "Limited Partnership" is valid and shouldn't be split
        result = NameSplitter.split_org_name("ABC Limited Partnership")
        assert result == ["ABC Limited Partnership"]

        # Trading-as patterns shouldn't be split
        result = NameSplitter.split_org_name("Company Ltd T/A Trading Name")
        assert result == ["Company Ltd T/A Trading Name"]

    def test_split_attendee_list_semicolon(self):
        """Semicolon-separated lists should be split correctly."""
        result = NameSplitter.split_attendee_list("Org A; Org B; Org C")
        assert result == ["Org A", "Org B", "Org C"]

    def test_split_attendee_list_and(self):
        """And-separated lists should be split correctly."""
        result = NameSplitter.split_attendee_list("Org A and Org B")
        assert result == ["Org A", "Org B"]

    def test_split_attendee_preserves_ampersand_in_names(self):
        """Known company names with ampersand should not be split."""
        result = NameSplitter.split_attendee_list("Marks & Spencer")
        assert result == ["Marks & Spencer"]

        result = NameSplitter.split_attendee_list("Procter & Gamble")
        assert result == ["Procter & Gamble"]

    def test_split_attendee_list_slash(self):
        """Slash-separated lists should be split correctly."""
        result = NameSplitter.split_attendee_list("Org A / Org B")
        assert result == ["Org A", "Org B"]

    def test_detect_delimiter_semicolon(self):
        """Semicolon delimiter should be detected."""
        assert NameSplitter.detect_delimiter("Org A; Org B") == ";"

    def test_detect_delimiter_slash(self):
        """Slash delimiter should be detected."""
        assert NameSplitter.detect_delimiter("Org A / Org B") == " / "

    def test_detect_delimiter_none(self):
        """No delimiter should return None."""
        assert NameSplitter.detect_delimiter("Single Organization") is None


class TestEventDescriptionParser:
    """Tests for EventDescriptionParser class."""

    def test_is_event_description_roundtable(self):
        """Roundtable events should be detected."""
        assert EventDescriptionParser.is_event_description("Roundtable on AI") is True
        assert EventDescriptionParser.is_event_description("Roundtable with Company A") is True
        assert EventDescriptionParser.is_event_description("Round table with stakeholders") is True

    def test_is_event_description_call(self):
        """Call events should be detected."""
        assert EventDescriptionParser.is_event_description("Call with Eurostar CEO") is True
        assert EventDescriptionParser.is_event_description("Phone call with Minister") is True

    def test_is_event_description_meeting(self):
        """Meeting events should be detected."""
        assert EventDescriptionParser.is_event_description("Meeting with industry stakeholders") is True

    def test_is_event_description_breakfast_lunch_dinner(self):
        """Meal events should be detected."""
        assert EventDescriptionParser.is_event_description("Breakfast with Tech CEOs") is True
        assert EventDescriptionParser.is_event_description("Lunch with CBI") is True
        assert EventDescriptionParser.is_event_description("Dinner with Ambassador") is True

    def test_is_event_description_false_for_org(self):
        """Organization names should not be detected as events."""
        assert EventDescriptionParser.is_event_description("Acme Corporation") is False
        assert EventDescriptionParser.is_event_description("Google UK") is False

    def test_extract_attendees_roundtable(self):
        """Attendees should be extracted from roundtable descriptions."""
        result = EventDescriptionParser.extract_attendees(
            "Roundtable with Company A, Company B"
        )
        assert len(result) == 2
        assert "Company A" in result
        assert "Company B" in result

    def test_extract_attendees_call_with_ceo(self):
        """CEO references should be extracted from call descriptions."""
        result = EventDescriptionParser.extract_attendees("Call with CEO of Google")
        # Extracts "CEO of Google" which can be processed further
        assert len(result) == 1
        assert "Google" in result[0]

    def test_extract_attendees_generic(self):
        """Generic descriptions extract whatever follows 'with'."""
        result = EventDescriptionParser.extract_attendees("Meeting with industry stakeholders")
        # The implementation extracts "industry stakeholders" as an attendee
        # This is intentional - further filtering happens during actor creation
        assert "industry stakeholders" in result

    def test_get_event_type(self):
        """Event types should be extracted correctly."""
        assert EventDescriptionParser.get_event_type("Roundtable on AI") == "roundtable"
        assert EventDescriptionParser.get_event_type("Call with CEO") == "call"
        assert EventDescriptionParser.get_event_type("Breakfast with CBI") == "breakfast"


class TestNameNormalizer:
    """Tests for NameNormalizer class."""

    def test_normalize_double_spaces(self):
        """Double spaces should be collapsed."""
        assert NameNormalizer.normalize("John  Smith") == "John Smith"
        assert NameNormalizer.normalize("Acme   Corporation   Ltd") == "Acme Corporation Ltd"

    def test_normalize_trailing_punctuation(self):
        """Trailing punctuation should be removed."""
        assert NameNormalizer.normalize("Company Name,") == "Company Name"
        assert NameNormalizer.normalize("Organization;") == "Organization"

    def test_normalize_leading_punctuation(self):
        """Leading punctuation should be removed."""
        assert NameNormalizer.normalize(", Company Name") == "Company Name"
        assert NameNormalizer.normalize("- Organization") == "Organization"

    def test_normalize_whitespace(self):
        """Leading/trailing whitespace should be trimmed."""
        assert NameNormalizer.normalize("  Company Name  ") == "Company Name"

    def test_has_quality_issues_double_spaces(self):
        """Double spaces should be detected as quality issue."""
        issues = NameNormalizer.has_quality_issues("John  Smith")
        assert "double_spaces" in issues

    def test_has_quality_issues_trailing_punctuation(self):
        """Trailing punctuation should be detected as quality issue."""
        issues = NameNormalizer.has_quality_issues("Company,")
        assert "trailing_punctuation" in issues

    def test_has_quality_issues_clean(self):
        """Clean names should have no issues."""
        issues = NameNormalizer.has_quality_issues("Clean Company Name")
        assert issues == []


class TestCamelCaseSplitter:
    """Tests for CamelCaseSplitter class."""

    def test_detect_camelcase_transitions(self):
        """CamelCase transitions should be detected."""
        positions = CamelCaseSplitter.detect_camelcase_transitions("CompanyName")
        assert 7 in positions  # Before 'N'

        positions = CamelCaseSplitter.detect_camelcase_transitions("AbcDefGhi")
        assert 3 in positions  # Before 'D'
        assert 6 in positions  # Before 'G'

    def test_should_split_multiple_transitions(self):
        """Names with multiple transitions should be flagged for splitting."""
        assert CamelCaseSplitter.should_split("CompanyLtdAnotherCompany") is True
        assert CamelCaseSplitter.should_split("FirstOrgSecondOrg") is True

    def test_should_split_single_transition(self):
        """Names with single transitions should not be split."""
        assert CamelCaseSplitter.should_split("CompanyName") is False

    def test_should_split_irish_names(self):
        """Irish/Scottish names should not be split."""
        assert CamelCaseSplitter.should_split("McDonald") is False
        assert CamelCaseSplitter.should_split("MacArthur") is False

    def test_split_concatenated(self):
        """Concatenated CamelCase names should be split."""
        result = CamelCaseSplitter.split("FirstOrgSecondOrg")
        assert len(result) >= 2

    def test_split_normal_name(self):
        """Names with single CamelCase transition should not be split."""
        # Single transition like "CompanyName" should not be split
        result = CamelCaseSplitter.split("CompanyName")
        assert result == ["CompanyName"]

        # Names with multiple transitions but appearing in normal patterns
        # need more context to determine if they should split
        result = CamelCaseSplitter.split("McDonald")  # Irish name
        assert result == ["McDonald"]
