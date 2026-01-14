# Data Models

The UnderTheInfluence data model is based on Popolo's open government data specifications. They offer rich, expressive data interchange formats and data models so that we can spend less time transforming and modeling data.

## Primary Data Sources

The application integrates data from multiple sources:

### Popolo-Based Sources

**ParlParse** (Primary parliamentary data)
- [people.json:](http://parser.theyworkforyou.com/members.html)
- Data of all MPs, Lords, MSPs and MLAs in Popolo format
- Includes names, party affiliations, constituencies, and peerage information
- Each membership represents a continuous period of holding office
- Imported via `import_parlparse` and `import_ministers`

**TheyWorkForYou** (Enrichment data)
- [API documentation](http://www.theyworkforyou.com/api/)
- Biographical data and external links (Wikipedia, BBC, MP websites)
- Enriches existing Person records with dates of birth and profile images
- Imported via `import_twfy`

### Influence Mapping Sources

**Electoral Commission** (Political donations)
- Donation data from parties, candidates, and third parties
- Creates Donation records linking donors to recipients
- Imported via `import_ec`

**PRCA Professional Lobbying Register** (Current lobbying data)
- Active lobbying agencies and their clients
- Creates Consultancy relationships between agencies and clients
- Imported via `import_appc`

**PRCA Historical Archive** (Historical lobbying data 2019-2025)
- 26 historical PDF registers
- Creates Organization, Consultancy, and Membership records
- Imported via `import_appc_archive`

**MPs' Register of Interests** (MPs' declared interests)
- Categories 2 (Donations) and 3 (Gifts/Hospitality)
- Creates Donation records with donor organizations/persons
- Imported via `import_mpsinterests`

**Lords' Register of Interests** (Lords' declared interests)
- Sponsorships, visits, and gifts
- Creates Donation records (donor=null for unstructured text)
- Imported via `import_lordsinterests`

---

For detailed import documentation, see `docs/importing-data.md` and `docs/data-import-testing.md`.

---

## Data Model Reference

These are the primary data models implemented for UnderTheInfluence, based on the Popolo specification.



## ```datafetch/influence_mapping.py```

#### ```class Relationship()```
*A relationship between two actors.*   
* http://popoloproject.com/schemas/membership.json 

| Field | Type | Notes |  
|-------|-----:|:------|  
|```label``` | ```CharField``` |  |  
|```links``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  
|```sources``` | ```URLField``` | http://popoloproject.com/schemas/link.json |   
|```identifiers``` | ```GenericRelation``` | http://popoloproject.com/schemas/identifier.json |


#### ```class Consultancy()```
*A lobbying relationship between a client organization and a lobbying agency.*

| Field | Type | Notes |
|-------|-----:|:------|
|```client``` | ```ForeignKey(Actor)``` | The organization being represented |
|```agency``` | ```ForeignKey(Actor)``` | The lobbying agency |

**Data Sources**: PRCA Professional Lobbying Register (current and historical 2019-2025)  


#### ```class Donation()```
*A political donation or declared interest.*

| Field | Type | Notes |
|-------|-----:|:------|
|```donor``` | ```ForeignKey(Actor)``` | The donor (may be null for Lords' interests) |
|```recipient ``` | ```ForeignKey(Actor)``` | The recipient (MP, Lord, or party) |
|```value ``` | ```DecimalField``` | The monetary value of the donation (0 for Lords) |
|```donation_type``` | ```CharField``` | The type of donation e.g. Cash, Visit, Gift, Sponsorship |
|```nature_of_donation``` | ```CharField``` | The nature of the donation e.g. hospitality |
|```received_date``` | ```DateField``` |  |
|```accepted_date``` | ```DateField``` |  |
|```reported_date``` | ```DateField``` |  |
|```accounting_unit_name``` | ```CharField``` |  |
|```accounting_units_as_central_party``` | ```BooleanField``` |  |
|```purpose_of_visit``` | ```CharField``` |  |
|```is_bequest``` | ```BooleanField``` |  |
|```is_aggregation``` | ```BooleanField``` |  |
|```is_sponsorship``` | ```BooleanField``` |  |

**Data Sources**:
- Electoral Commission (91,281+ donation records)
- MPs' Register of Interests (Categories 2 & 3)
- Lords' Register of Interests (Sponsorship, Visits, Gifts)  


## ```datafetch/models.py```

#### ```class Actor()```

| Field | Type | Notes |  
|-------|-----:|:------|  
|```name``` | ```CharField``` |  |  
|```image``` | ```URLField``` |  |  
|```other_names``` | ```GenericRelation``` | http://popoloproject.com/schemas/other_name.json |  
|```identifiers``` | ```GenericRelation``` | http://popoloproject.com/schemas/identifier.json |  
|```contact_details``` | ```GenericRelation``` | http://popoloproject.com/schemas/contact_detail.json |
|```links``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  
|```sources``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  
|```notes``` | ```GenericRelation``` |  |  



#### ```class Person(Actor)```
*A real person, alive or dead.*   
* http://popoloproject.com/schemas/person.json

| Field | Type | Notes |  
|-------|-----:|:------|  
|```json_ld_context``` |  |  |  
|```json_ld_type``` |  |  |  
|```family_name``` | ```CharField``` |  |   
|```given_name``` | ```CharField``` |  |   
|```additional_name``` | ```CharField``` |  |   
|```honorific_prefix``` | ```CharField``` |  |   
|```honorific_suffix``` | ```CharField``` |  |   
|```patronymic_name``` | ```CharField``` |  |   
|```sort_name``` | ```CharField``` |  |   
|```email``` | ```CharField``` |  |    
|```gender``` | ```CharField``` |  |   
|```birth_date``` | ```CharField``` |  |   
|```death_date``` | ```CharField``` |  |    
|```summary``` | ```CharField``` |  |    
|```biography``` | ```CharField``` |  |   
|```national_identity``` | ```CharField``` |  |   



#### ```class Organization(Actor)```
*A group with a common purpose or reason for existence that goes beyond the set of people belonging to it.*   
* http://popoloproject.com/schemas/organization.json

| Field | Type | Notes |  
|-------|-----:|:------|  
|```summary``` | ```CharField``` |  |  
|```description``` | ```TextField``` |  |  
|```classification``` | ```CharField``` | |  
|```parent ``` | ```ForeignKey``` | http://popoloproject.com/schemas/organization.json |  
|```area``` | ```ForeignKey``` | http://popoloproject.com/schemas/area.json |
|```dissolution_date``` | ```CharField``` |  |  
|```founding_date``` | ```CharField``` |  |  
|```url_name``` | organization-detail |  |



#### ```class Post()```
*A position that exists independent of the person holding it.*  
* http://popoloproject.com/schemas/post.json   

| Field | Type | Notes |  
|-------|-----:|:------|  
|```label``` | ```CharField``` |  |  
|```other_label``` | ```CharField``` |  |  
|```organization``` | ```ForeignKey``` | http://popoloproject.com/schemas/organization.json |  
|```area``` | ```ForeignKey``` | http://popoloproject.com/schemas/area.json |  
|```contact_details``` | ```GenericRelation``` | http://popoloproject.com/schemas/contact_detail.json |
|```links``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  
|```sources``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  



#### ```class Membership()```
*A relationship between a person and an organization*  
* http://popoloproject.com/schemas/membership.json   

| Field | Type | Notes |  
|-------|-----:|:------|  
|```label``` | ```CharField``` |  |  
|```role``` | ```CharField``` |  |  
|```person``` | ```ForeignKey``` | http://popoloproject.com/schemas/person.json |  
|```organization``` | ```ForeignKey``` | http://popoloproject.com/schemas/organization.json |  
|```on_behalf_of``` | ```ForeignKey``` |  |
|```post``` | ```ForeignKey``` | http://popoloproject.com/schemas/post.json |
|```area``` | ```ForeignKey``` | http://popoloproject.com/schemas/area.json |
|```contact_details``` | ```GenericRelation``` | http://popoloproject.com/schemas/contact_detail.json |
|```links``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  
|```sources``` | ```GenericRelation``` | http://popoloproject.com/schemas/link.json |  


#### ```class Identifier()```
*An issued identifier.*  
* http://popoloproject.com/schemas/identifier.json   

| Field | Type | Notes |  
|-------|-----:|:------|  
|```identifier``` | ```CharField``` | An issued identifier, e.g. a DUNS number |  
|```scheme``` | ```CharField``` | An identifier scheme, e.g. DUNS |  


#### ```class Link()```
*A URL.*   
* http://popoloproject.com/schemas/link.json


#### ```class Source()```
*A URL for referring to sources of information.*
* http://popoloproject.com/schemas/source.json#


| Field | Type | Notes |  
|-------|-----:|:------|  
|```url``` | ```CharField``` | A URL |  
|```note``` | ```CharField``` | A note, e.g. 'Parliament website' |  


#### ```class ContactDetail()```
*A means of contacting an entity.*   
* http://popoloproject.com/schemas/contact-detail.json


#### ```class OtherName()```
*An alternate or former name.*
* http://popoloproject.com/schemas/name-component.json


#### ```class Area()```
*An area is a geographic area whose geometry may change over time.*
* http://popoloproject.com/schemas/area.json

**Note**: The `Area.classification` field has an incorrect verbose name in the model ("identifier" instead of "classification"). See `docs/data_modeling_review.md` for details.

