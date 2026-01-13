# Data Modeling Approach Review - UnderTheInfluence Project

**Date**: January 12, 2026
**Author**: Gemini CLI Agent
**Context**: Review of the data modeling approach based on existing code (`datafetch/models/models.py`, `datafetch/models/influence_mapping.py`, `datafetch/models/popolo/behaviors.py`) and documentation (`docs/data-models.md`, `docs/systems-architecture.md`).

## 1. Overall Suitability

The data modeling approach for the UnderTheInfluence project is **highly suitable** for its stated goal of tracking and exposing influence in UK politics. It leverages the strengths of Django's ORM in conjunction with established open-data standards and best practices for flexible and extensible data representation.

## 2. Strengths of the Current Approach

1.  **Popolo Standard Adoption**:
    *   **Rationale**: Explicit adoption of the Popolo Project's open government data specification (`Actor`, `Person`, `Organization`, `Post`, `Membership`, `Identifier`, `OtherName`, `Link`, `Source`, `Area`) provides a robust, comprehensive, and well-defined schema.
    *   **Benefits**: Ensures interoperability with other civic tech projects, reduces data transformation overhead when importing from Popolo-compliant sources (like ParlParse and EveryPolitician), and benefits from a community-maintained standard.

2.  **Polymorphic Models for Actors (`django-polymorphic`)**:
    *   **Rationale**: The `Actor` base class, implemented using `django-polymorphic`, allows `Person` and `Organization` to inherit common attributes and relationships.
    *   **Benefits**: Simplifies queries across both entity types (e.g., a single search function for all actors), centralizes shared logic, and allows foreign keys (e.g., `donor`, `recipient`) to reference any type of actor.

3.  **Extensive Use of Generic Relations**:
    *   **Rationale**: `GenericRelation` (leveraging Django's ContentType framework) is used for attaching flexible metadata like `other_names`, `identifiers`, `contact_details`, `links`, `sources`, and `notes` to various entities.
    *   **Benefits**: Keeps core models clean by avoiding numerous specific `ForeignKey` fields, provides a consistent interface for managing diverse metadata, and is highly flexible for future model extensions without rigid schema changes. This aligns well with Popolo's flexible metadata approach.

4.  **Abstract Behavior Models (`Timestampable`, `Dateframeable`, `GenericRelatable`)**:
    *   **Rationale**: These abstract base classes (`datafetch/models/popolo/behaviors.py`) encapsulate common fields and functionalities (e.g., `created_at`/`updated_at` timestamps, `start_date`/`end_date` date ranges, generic relation fields).
    *   **Benefits**: Promotes the DRY (Don't Repeat Yourself) principle, ensures data consistency across models, and simplifies model definitions.

5.  **Robust Partial Date Handling**:
    *   **Rationale**: Storing dates as `CharField` (YYYY, YYYY-MM, or YYYY-MM-DD formats) with custom validators (`validate_partial_date`, `RegexValidator`) is a pragmatic solution for political data where precise dates are often unavailable.
    *   **Benefits**: Accurately reflects the nuances of source data, allows for lexicographical ordering, and aligns with Popolo specifications for date representation.

6.  **Clear Domain Mapping for Relationships**:
    *   **Rationale**: Explicit models like `Donation` and `Consultancy` (inheriting from an abstract `Relationship` base) provide domain-specific fields and clear semantics for key influence relationships.
    *   **Benefits**: Enhances type safety, improves readability, and provides a clear structure for API design and querying.

## 3. Areas for Improvement / Further Consideration

While the overall approach is strong, the following points highlight minor areas for refinement or clarification:

1.  **Source Information Redundancy (`Relationship.source` vs. `GenericRelation('Source')`)**:
    *   **Issue**: The `Relationship` abstract model includes a `source = models.URLField`, but it also inherits `sources = GenericRelation('Source')` via `GenericRelatable`. This creates redundancy and potential confusion about the intended mechanism for storing source information.
    *   **Recommendation**: Standardize on one approach. The `GenericRelation('Source')` offers greater flexibility (allowing multiple sources, notes, etc.) and is generally preferred for richer metadata. The `URLField` might be simplified or removed if the GenericRelation is chosen.

2.  **`Donation` Model `start_date` Override**:
    *   **Issue**: The `Donation` model defines a `start_date` *property* that returns `self.accepted_date`, while `Dateframeable` (its ancestor) defines `start_date` as a `CharField` field. This overlap is confusing and could lead to unexpected behavior if code accesses the `start_date` field directly instead of the property.
    *   **Recommendation**: Clarify intent. If `accepted_date` is the definitive start date for donations, consider either:
        *   Removing `start_date` from `Dateframeable` if it's not universally applicable.
        *   Renaming `Dateframeable`'s `start_date` to something like `raw_start_date` and consistently deriving the "effective" start date.
        *   Explicitly populating `Donation.start_date` (inherited from `Dateframeable`) with `accepted_date` during saving, and then removing the property.

3.  **`Dateframeable` Property Naming and Return Type (`start_datetime`, `end_datetime`)**:
    *   **Issue**: The `start_datetime` and `end_datetime` properties return formatted strings (e.g., "Jan 2024") or the raw partial date string, not actual `datetime` objects as their names suggest.
    *   **Recommendation**: Rename these properties to `formatted_start_date` and `formatted_end_date` for clarity if they are intended to return strings. Alternatively, modify them to return actual `datetime.date` or `datetime` objects (e.g., representing the start/end of the partial period) for more programmatic use and consistency with "datetime" in their names.

4.  **`Membership.label` vs. `Membership.role`**:
    *   **Issue**: The `Membership` model includes both `label` and `role` fields, both being `CharField`. Their distinct purposes are not immediately clear from the model definition. Popolo's `Membership` schema primarily uses `role`.
    *   **Recommendation**: Clarify the semantic distinction. If `label` is redundant or serves a very similar purpose, consider consolidating. If both are necessary, document their intended use cases.

5.  **Enforcing Donation Choices (`CATEGORY_CHOICES`, `NATURE_CHOICES`)**:
    *   **Issue**: `CATEGORY_CHOICES` and `NATURE_CHOICES` are defined in the `Donation` model but are not applied to the `donation_type` and `nature_of_donation` fields using the `choices=...` argument.
    *   **Recommendation**: Apply these choices to the respective fields to ensure data integrity, restrict input to predefined values, and improve form rendering in the admin interface.

6.  **Documentation Alignment and Consistency**:
    *   **Issue**: `docs/data-models.md` has a few inconsistencies:
        *   `Link` model appears twice.
        *   `Post` model's schema comment points to `http://popoloproject.com/schemas/json#` (too generic) instead of `http://popoloproject.com/schemas/post.json#`.
        *   `Source` model's schema comment points to `http://popoloproject.com/schemas/link.json#`, but Popolo has a more specialized `Source` schema.
    *   **Recommendation**: Review and update `docs/data-models.md` to ensure it accurately reflects the current model definitions and correct Popolo schema references.

7.  **Minor Model Field Verbose Name Typo**:
    *   **Issue**: In `datafetch/models/models.py`, `Area.classification` field's verbose name is `_("identifier")`.
    *   **Recommendation**: Correct the verbose name to `_("classification")` for accuracy.

## 4. Clarifying Questions for the Project Owner

To further refine this assessment and guide future development, the following questions are posed:

1.  **Source Information Redundancy**: The `Relationship` model (and thus `Consultancy` and `Donation`) has both a `source = models.URLField` and inherits `sources = GenericRelation('Source')`. Which mechanism is preferred for storing source information for these models? Should the `URLField` be removed in favor of `GenericRelation` for consistency and richer metadata?
2.  **`Donation` Model `start_date` Behavior**: The `Donation` model has a `start_date` *property* that returns `self.accepted_date`, which overrides the `start_date` `CharField` inherited from `Dateframeable`. Was this property override intentional for temporal filtering, or should `Dateframeable`'s `start_date` field be consistently populated for all inheriting models?
3.  **`Dateframeable` Property Naming**: The `start_datetime` and `end_datetime` properties in `popolo/behaviors.py` return formatted strings (e.g., "Jan 2024") rather than actual `datetime` objects. Is this intended behavior, or would renaming them (e.g., `formatted_start_date`) or modifying them to return `datetime` objects improve clarity and utility?
4.  **`Membership.label` vs. `Membership.role`**: Could you clarify the intended distinction and usage guidelines for the `label` and `role` fields in the `Membership` model?
5.  **Enforcing Donation Choices**: Are the `CATEGORY_CHOICES` and `NATURE_CHOICES` defined in the `Donation` model meant to be enforced for the `donation_type` and `nature_of_donation` fields? If so, applying them using the `choices=...` argument in the field definitions would enhance data integrity.
6.  **`Area` Model Verbose Names**: Is the verbose name for the `Area.classification` field correctly `_("identifier")` or should it be `_("classification")`?
