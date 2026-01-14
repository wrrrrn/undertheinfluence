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
| Person ids |  ```Identifier``` |   
| Person other names |  ```OtherName``` |  
| People |  ```Person``` |   
| Political parties, legislature, |  ```Organization``` |   
| Posts | ```Post``` |  
| Memberships | ```Membership``` |


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
| Political parties |  ```Organization``` |   
| Ministers |  ```Person``` |  
| Memberships |  ```Membership``` |    


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
* Data is fetched / saved in csv format from [search.electoralcommission.org.uk/api/csv/Donations](http://search.electoralcommission.org.uk/api/csv/Donations)

__Parsing & importing__  
The csv parsed and saved into the following data models:
  
| Information | Data Model |  
|--------------|------------:|  
| ECRefs |  ```Identifier``` |     
| Company registration no. |  ```Identifier``` |    
| Individual donors |  ```Person``` |   
| Company / organisation donors |  ```Organization``` |   
| Donor postcodes | ```ContactDetails``` |   
| Individual recipients |  ```Person``` |   
| Political parties |  ```Organization``` |  
| Donations |  ```Donation``` |  
|  |  ```Note``` |   


## TheyWorkForYou

> TheyWorkForYou lets you find out what your MP, MSP or MLA is doing in your name, read debates, written answers

We use the TheyWorkForYou API to enrich existing MP records with biographical data and external links.

__Data sources__
* [TheyWorkForYou](http://www.theyworkforyou.com/api/)

__Usage__
```
python manage.py import_twfy --since 2010
```

__Current status__
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* Uses the TheyWorkForYou API to fetch MP enrichment data. Requires `TWFY_API_KEY` in `.env` file.

__Parsing & importing__
This command enriches existing Person records (imported via parlparse) with additional data:

| Information | Data Model |
|--------------|------------:|
| Wikipedia URL | ```Link``` |
| BBC Profile URL | ```Link``` |
| MP Website URL | ```Link``` |
| Guardian Profile URL | ```Link``` |
| Date of birth | ```Person.birth_date``` |
| Profile image | ```Person.image``` |

**Notes**:
- Only enriches MPs already in the database (matched by uk.org.publicwhip identifier)
- Does not duplicate core parliamentary data (that comes from parlparse)
- May experience SSL/network errors with TheyWorkForYou API on large imports
- Progress indicator shows every 50 MPs processed


## Register of Members’ Financial Interests

We mine MP's declared interests outside to record the monetary value of declared interests and well as the individuals / organisations with whom they have these interests.
 
__Data sources__  
* [theyworkforyou](https://www.theyworkforyou.com/pwdata/scrapedxml/regmem/)

__Usage__  
```
python manage.py import_mpsinterests
```
__Current status__  
- [x] fetching
- [x] parsing
- [x] importing


__Fetching__
* Current data is fetched / saved in xml format from [theyworkforyou.com/pwdata/scrapedxml/regmem](https://www.theyworkforyou.com/pwdata/scrapedxml/regmem/) using `curl`.
* The command no longer requires a git submodule and handles historical downloads directly.

__Parsing & importing__  
XML files are parsed using BeautifulSoup. Data from Category 2 (Donations) and Category 3 (Gifts/Hospitality) are imported as `Donation` records, linked to the respective MPs. New donors (People or Organizations) are created automatically.


## Register of Lords' Financial Interests

We mine Lords' declared interests to record sponsorships, overseas visits, and gifts received by members of the House of Lords.

__Data sources__
* [data.parliament.uk](http://data.parliament.uk/)

__Usage__
```
python manage.py import_lordsinterests
```

__Current status__
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* Current data is fetched / saved in JSON format from [data.parliament.uk](http://data.parliament.uk/membersdataplatform/services/mnis/members/query/House=Lords/Interests%7CPreferredNames/)

__Parsing & importing__
JSON data is parsed and imported as `Donation` records. The parser extracts interests from Categories 4 (Sponsorship), 5 (Overseas visits), and 6 (Gifts).

| Information | Data Model |
|--------------|------------:|
| Lords' declared interests |  ```Donation``` |
| Full interest text (if truncated) |  ```Note``` |
| Interest identifiers |  ```Identifier``` |

**Notes**:
- Donor information is not extracted (embedded in unstructured text) - `donor=null`
- Monetary values are not reported for Lords' interests - `value=0`
- Full text is preserved in Note objects when it exceeds the 128-character field limit
- Deduplication uses `lords_interest` identifier scheme


## PRCA Public Affairs Register (Current)
> The Public Relations and Communications Association (PRCA) is the representative body for PR and communications practitioners, formed after merging with the APPC.

We mine this data to build a list of __lobbying agencies__, their __employees__ and their __clients__ from the current register.

__Data sources__  
* [PRCA Professional Lobbying Register](https://www.prca.global/professional-lobbying-register)

__Usage__  
```
python manage.py import_appc
```

__Current status__  
- [x] fetching
- [x] parsing
- [x] importing

__Fetching__
* The list of agencies and their clients is scraped from the current live register page. The command handles pagination to fetch all entries.

__Parsing & importing__  
Data is scraped from the page and saved into the following data models:

| Information | Data Model |  
|--------------|------------:|  
| Lobby agencies |  ```Organization``` |   
| Lobby agency contact details| ```ContactDetail``` |  
| Lobby agency employees | ```Person``` |  
| Clients |  ```Organization```  |  
| Lobby agency / client relationships | ```Consultancy``` |  

## PRCA Historical Register (PDF Archive)

> The Public Relations and Communications Association (PRCA) provides an archive of historical lobbying registers in PDF format covering 2019-2025.

__Data sources__
* [PRCA Public Affairs Register - Previous Registers](https://www.prca.global/sspx/public-affairs-register-previous-registers)

__Usage__
```
python manage.py import_appc_archive
```

__Current status__
- [x] fetching PDF links
- [x] parsing (via PyMuPDF)
- [x] importing

__Fetching__
* The command processes 26 historical PDF registers from the `data/appc_archive/` directory.

__Parsing__
* Uses `PyMuPDF` (fitz) with font-based heuristics to reliably parse varied PDF layouts (single-column and two-column) from 2019 to 2025.
* Extracts Company Name, Address, Contact Details, Practitioners, Clients, and Countries of Operation.

__Importing__
Data is imported into the following models:

| Information | Data Model |
|--------------|------------:|
| Lobbying agencies | ```Organization``` |
| Agency addresses | ```ContactDetail``` |
| Agency emails/websites | ```ContactDetail``` / ```Link``` |
| Practitioners | ```Person``` + ```Membership``` |
| Clients | ```Organization``` |
| Agency-client relationships | ```Consultancy``` |

**Notes**:
- Processes ~3,000 agencies and ~26,000 consultancy relationships across 26 PDFs
- Addresses automatically truncated to 512 characters when necessary
- Some Q3 2025 entries have overly long company names that exceed database limits (23/73 failed)
  


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
| Politicans |  ```Person``` |  


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
* Each company profile is saved in json format to the `data/companieshouse` folder

__Parsing & importing__  
The saved json is parsed and if a company exists within our data set it is updated with the extra information.  

Data models used:

| Information | Data Model |  
--------------|------------:|  
| Companies |  ```Organization``` |  




