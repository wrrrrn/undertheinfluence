from bs4 import BeautifulSoup
import logging

logger = logging.getLogger(__name__)

class MPsInterestsParser:
    def parse(self, xml_path):
        """
        Parses a TWFY MPs' Interests XML file.
        Returns a list of dicts, one per MP entry.
        """
        try:
            with open(xml_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read file {xml_path}: {e}")
            return []
        
        soup = BeautifulSoup(content, 'xml')
        
        results = []
        for regmem in soup.find_all('regmem'):
            person_data = {
                'person_id': regmem.get('personid'),
                'member_name': regmem.get('membername'),
                'date': regmem.get('date'),
                'interests': []
            }
            
            for category in regmem.find_all('category'):
                cat_type = category.get('type')
                cat_name = category.get('name')
                
                # The content inside <record> seems to be HTML wrapped in <item>
                # Sometimes there are multiple records/items
                for item in category.find_all('div', class_='interest-item'):
                    interest = {
                        'category_type': cat_type,
                        'category_name': cat_name,
                        'id': item.get('id'),
                        'summary': item.find('h4', class_='interest-summary').get_text(strip=True) if item.find('h4', class_='interest-summary') else '',
                        'details': {}
                    }
                    
                    for detail in item.find_all('li', class_='interest-detail'):
                        name_span = detail.find('span', class_='interest-detail-name')
                        value_span = detail.find('span', class_='interest-detail-value')
                        if name_span and value_span:
                            key = name_span.get_text(strip=True).rstrip(':')
                            val = value_span.get_text(strip=True)
                            interest['details'][key] = val
                    
                    # Also get dates
                    reg_date = item.find('li', class_='registration-date')
                    if reg_date:
                        interest['registration_date'] = reg_date.get_text(strip=True).replace('Registration Date: ', '')
                        
                    pub_date = item.find('li', class_='published-date')
                    if pub_date:
                        interest['published_date'] = pub_date.get_text(strip=True).replace('Published Date: ', '')

                    person_data['interests'].append(interest)
            
            results.append(person_data)
        
        return results
