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
These the data models implemented for UnderTheIfluence

## ```datafetch/models.py```

#### class Actor()

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



#### class Person(*Actor*)
*A real person, alive or dead.*   
http://popoloproject.com/schemas/person.json

| Field | Type | Notes |  
|-------|-----:|:------|  
|```json_ld_context``` |  |  |  
|```json_ld_type``` |  |  |  
|```family_name``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```given_name``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```additional_name``` | ```CharField``` | http://popoloproject.com/schemas/person.json |
|```honorific_prefix``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```honorific_suffix``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```patronymic_name``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```sort_name``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```email``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```gender``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```birth_date``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```death_date``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```summary``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```biography``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  
|```national_identity``` | ```CharField``` | http://popoloproject.com/schemas/person.json |  



#### class Organization(*Actor*)
*A group with a common purpose or reason for existence that goes beyond the set of people belonging to it.*   
http://popoloproject.com/schemas/organization.json

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



#### class Post()
*A position that exists independent of the person holding it.*  
http://popoloproject.com/schemas/post.json   

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
