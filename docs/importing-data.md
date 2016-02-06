# Importing Data

Data is imported with the following Django management commands found in `datafetch/management/commands`. Each command __fetches__, __parses__ and __imports data__ into the system.

Management commands have been implemented for the following data sources:

## MySociety ParlParse

> Data of all MPs, Lords, MSPs and MLAs covered by the project, in Popolo format, including names (and alternate names such as misspellings or name changes), party, constituency (non-Lords), and peerage information (Lords). There is a unique identifier for each element.   

__Data sources__  
* [ParlParse](parser.theyworkforyou.com)  

__Usage__  
```
python manage.py import_parlparse --since 2010
```
__Current status__  
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* Current data is saved from [cdn.rawgit.com/mysociety/parlparse/master/members/people.json](https://cdn.rawgit.com/mysociety/parlparse/master/members/people.json)

__Parsing & importing__  
people.json is parsed and and saved into the following data models:
  
| Information | Data Model |  
|--------------|------------:|  
| Person ids |  Identifier |   
| Person other names |  OtherName |  
| People |  Person |   
| Political parties, legislature, |  Organizations |   
| Posts |  Post |  
| Memberships |  Membership |


## MySociety ParlParse - Ministers

__Data sources__  
* [ParlParse](parser.theyworkforyou.com)  

__Usage__  
```
python manage.py import_ministers --since 2010
```
__Current status__  
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* Current data is saved from [cdn.rawgit.com/mysociety/parlparse/master/members/ministers.json](https://cdn.rawgit.com/mysociety/parlparse/master/members/ministers.json)

__Parsing & importing__  
ministers.json is parsed and and saved into the following data models:
  
| Information | Data Model |  
|--------------|------------:|  
| Political parties |  Organization |   
| Ministers |  Person |  
| Memberships |  Membership |   


## The Electoral Commission
> The independent elections watchdog and regulator of party and election finance

We mine this data for records of donations to politicians and political parties
 
__Data sources__  
* [The Electoral Commission](http://www.electoralcommission.org.uk/)

__Usage__  
```
python manage.py import_ec
```
__Current status__  
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* Data is fetched / saved in csv format [search.electoralcommission.org.uk/api/csv/Donations](http://search.electoralcommission.org.uk/api/csv/Donations)

__Parsing & importing__  
The csv parsed and and saved into the following data models:
  
| Information | Data Model |  
|--------------|------------:|  
| ECRefs |  Identifier |   
| Company registration no. |  Identifier |  
| Individual donors |  Person |   
| Company / organisation donors |  Organization |   
| Donor postcodes |  ContactDetails |   
| Individual recipients |  Person |   
| Political parties |  Organization |  
| Donations |  Donation |  
|  |  Note |   


## TheyWorkForYou

> TheyWorkForYou lets you find out what your MP, MSP or MLA is doing in your name, read debates, written answers   

__Data sources__  
* [TheyWorkForYou](http://www.theyworkforyou.com/api/)  

__Usage__  
```
python manage.py import_twfy
```
__Current status__  
- [x] fetching
- [ ] parsing
- [ ] importing

__Fetching__
* Current data is fetched / saved in json format from [theyworkforyou.com/api](http://www.theyworkforyou.com/api/)

__Parsing & importing__  
* __\#TODO__


## Register of Members’ Financial Interests

We mine MP's declared interests outside to record the monetary value of declared interests and well as the individuals / organisations with whom they have these interests.
 
__Data sources__  
* [theyworkforyou](http://www.theyworkforyou.com/pwdata/scrapedxml/regmem/)

__Usage__  
```
python manage.py import_mpsinterests
```
__Current status__  
- [x] fetching
- [ ] parsing
- [ ] importing


__Fetching__
* Historical records should be fetched with `git submodule update`
* Current data is fetched / saved in xml format from [theyworkforyou.com/pwdata/scrapedxml/regmem](http://www.theyworkforyou.com/pwdata/scrapedxml/regmem/)

__Parsing & importing__  
* __\#TODO__


## Register of Lords’ Financial Interests

We mine MP's declared interests outside to record the monetary value of declared interests and well as the individuals / organisations with whom they have these interests.
 
__Data sources__  
* [data.parliament.uk](http://data.parliament.uk/)
__Usage__  
```
python manage.py import_lordsinterests
```
__Current status__  
- [x] fetching
- [ ] parsing
- [ ] importing

__Fetching__
* Current data is fetched / saved in xml format from [data.parliament.uk](http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Lords/Interests%7CPreferredNames/)

__Parsing & importing__  
* __\#TODO__


## Association of Professional Political Consultants
> The Association of Professional Political Consultants is the self-regulatory and representative body for professional political practitioners

We mine this data to build a list of __lobbying agencies__, their __employees__ and their __clients__. 

__Data sources__  
* [Association of Professional Political Consultants](http://www.appc.org.uk)

__Usage__  
```
python manage.py import_appc
```

__Current status__  
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* The list of agencies is scraped from [appc.org.uk/members/register](http://www.appc.org.uk/members/register/)
* Each individual agency profile is saved to the data/appc folder

__Parsing & importing__  
Data is scraped from the saved pages and saved into the following data models:

| Information | Data Model |  
--------------|------------:|  
| Lobby agencies |  Organisation |   
| Lobby agency contact details| ContactDetail |  
| Lobby agency employees | Person |  
| Clients |  Person  |  
| Lobby agency / client relationships | Consultancy |  


## EveryPolitician

> EveryPolitician aims to provide data about, well, every politician. In the world.   

__Data sources__  
* [EveryPolitician](http://everypolitician.org/uk/)  

__Usage__  
```
python manage.py import_everypolitician
```
__Current status__  
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* Current data is fetched / saved in json format from [cdn.rawgit.com/everypolitician/everypolitician-data/master/data/UK/Commons/ep-popolo-v1.0.json](https://cdn.rawgit.com/everypolitician/everypolitician-data/master/data/UK/Commons/ep-popolo-v1.0.json)

__Parsing & importing__  
This data is used to update the following model:

| Information | Data Model |  
--------------|------------:|  
| Politicans |  Person |  


## Extra company / organizational data
This fetches and updates saved entities with extra organizational data.  

__Data sources__  
* [Companies House](https://www.gov.uk/government/organisations/companies-house)
* [Open Corporates](https://api.opencorporates.com/)

__Usage__  
```
python manage.py import_companieshouse
```
__Current status__  
- [x] fetching
- [ ] parsing
- [ ] importing

__Fetching__
* Each company profile is saved in json format to the data/companieshouse folder

__Parsing & importing__  
The saved json is parsed and if a company exists within our data set it is updated with the extra information.  

Data models used:

| Information | Data Model |  
--------------|------------:|  
| Companies |  Organisation |  




