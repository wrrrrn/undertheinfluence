# Data Models  

The UnderTheInfluence data model is mostly based on Popolo's open government data specifications. They offer rich, expressive data interchange formats and data models so that we can spend less time transforming and modeling data.   

There are currently two data sources, __EveryPolitician__ and __ParlParse__, that provide data based the Popolo specifications.  

## EveryPolitician
[Popolo JSON data:](http://docs.everypolitician.org/use_the_data.html#json-data)

> Popolo is an open standard for expressing political data — exactly for the kind of thing we’re doing here. So we provide our data in JSON format too, complying with Popolo standard. 

> A note about the Popolo standard: it’s a rich, expressive format that, like a language, is used in many different ways by different authors. However, when we add data to EveryPolitician we always use Popolo according to the same, defined principles. It’s because of this consistency that the tools you build will work with EveryPolitician data from any country, for any country.


## ParlParse
[people.json:](http://parser.theyworkforyou.com/members.html)
> Data of all MPs, Lords, MSPs and MLAs covered by the project, in Popolo format, including names (and alternate names such as misspellings or name changes), party, constituency (non-Lords), and peerage information (Lords). There is a unique identifier for each element. Each membership is a continuous period of holding office, loyal to the same party.

---
These the primary data models implemented for UnderTheIfluence

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
* http://popoloproject.com/schemas/link.json


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


#### ```class Link()```
*A URL.*   
* http://popoloproject.com/schemas/link.json


#### ```class Area()```
*An area is a geographic area whose geometry may change over time..*   
* http://popoloproject.com/schemas/area.json