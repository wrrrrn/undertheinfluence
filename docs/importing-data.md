# Importing Data

Data is imported with the following Django management commands found in datafetch/management/commands. These imports fetch, parse and import data into the system.

The imports currently implemented are:

## import_appc
```
python manage.py import_appc
```

> The [Association of Professional Political Consultants](http://www.appc.org.uk) is the self-regulatory and representative body for professional political practitioners

We mine this data to build a list of __lobbying agencies__, their __employees__ and their __clients__. 

### fetching
* The list of agencies is scraped (using BeautifulSoup) from [http://www.appc.org.uk/members/register/](http://www.appc.org.uk/members/register/)
* Each individual agency profile is saved to the data/appc folder

### parsing / importing
Data is scraped from the saved pages and saved into the following data models:

| Information | Data Model |  
| Lobby agency|  __Organisation__ |   
| Lobby agency contact details| __ContactDetail__ |  
| Lobby agency Employee |  __Person__ |  
| Client |  __Person__ |  
| Lobby agency / client relationship |  __Consultancy__ |  


