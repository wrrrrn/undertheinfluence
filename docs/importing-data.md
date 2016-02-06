# Importing Data

Data is imported with the following Django management commands found in datafetch/management/commands. These imports fetch, parse and import data into the system.

The imports currently implemented are:


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
* fetching: `working`
* parsing: `working`
* importing: `working`

__Fetching__
* Data is fetched / saved in csv format [search.electoralcommission.org.uk/api/csv/Donations](http://search.electoralcommission.org.uk/api/csv/Donations)

__Parsing & importing__  
The csv parsed and and saved into the following data models:
  
| Information | Data Model |  
|--------------|------------:|  
| ECRef |  Identifier |   
| Company registration no. |  Identifier |  
| Individual donor |  Person |   
| Company / organisation donor |  Organization |   
| Donor postcode |  ContactDetails |   
| Individual recipient |  Person |   
| Political Party |  Organization |  
| Donation |  Donation |  
|  |  Note |   


## Register of Lords’ Financial Interests

We mine MP's declared interests outside to record the monetary value of declared interests and well as the individuals / organisations with whom they have these interests.
 
__Data sources__  
* [data.parliament.uk](http://data.parliament.uk/)
__Usage__  
```
python manage.py import_lordsinterests
```
__Current status__  
* fetching: `working`
* parsing: `not started`
* importing: `not started`

__Fetching__
* Current data is fetched / saved in xml format [data.parliament.uk](http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Lords/Interests%7CPreferredNames/)


## Register of Members’ Financial Interests

We mine MP's declared interests outside to record the monetary value of declared interests and well as the individuals / organisations with whom they have these interests.
 
__Data sources__  
* [theyworkforyou](http://www.theyworkforyou.com/pwdata/scrapedxml/regmem/)

__Usage__  
```
python manage.py import_mpsinterests
```
__Current status__  
* fetching: `working`
* parsing: `not started`
* importing: `not started`

__Fetching__
* Historical records should be fetched with `git submodule update`
* Current data is fetched / saved in xml format [theyworkforyou.com/pwdata/scrapedxml/regmem](http://www.theyworkforyou.com/pwdata/scrapedxml/regmem/)



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
* fetching: `working`
* parsing: `working`
* importing: `working`

__Fetching__
* The list of agencies is scraped from [appc.org.uk/members/register](http://www.appc.org.uk/members/register/)
* Each individual agency profile is saved to the data/appc folder

__Parsing & importing__  
Data is scraped from the saved pages and saved into the following data models:

| Information | Data Model |  
--------------|------------:|  
| Lobby agency|  Organisation |   
| Lobby agency contact details| ContactDetail |  
| Lobby agency employee | Person |  
| Client |  Person  |  
| Lobby agency / client relationship | Consultancy |  


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
* fetching: `not working`
* parsing: `unknown`
* importing: `unknown`

__Fetching__
* Each company profile is saved in json format to the data/companieshouse folder

__Parsing & importing__  
The saved json is parsed and if a company exists within our data set it is updated with the extra information.  

Data models used:

| Information | Data Model |  
--------------|------------:|  
| Company |  Organisation |  




