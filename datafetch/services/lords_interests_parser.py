import json
import logging

logger = logging.getLogger(__name__)

class LordsInterestsParser:
    def parse(self, json_path):
        """
        Parses a Parliament Lords' Interests JSON file.
        Returns a list of dicts, one per Lord.
        """
        # Try different encodings (UK data may have various encodings)
        data = None
        for encoding in ['utf-8-sig', 'utf-8', 'iso-8859-1', 'windows-1252']:
            try:
                with open(json_path, 'r', encoding=encoding) as f:
                    data = json.load(f)
                break
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            except Exception as e:
                logger.error(f"Failed to read file {json_path}: {e}")
                return []

        if data is None:
            logger.error(f"Failed to read file {json_path}: Unable to decode with any encoding")
            return []
        
        results = []
        
        members = data.get('Members', {}).get('Member', [])
        if isinstance(members, dict):
            members = [members]
            
        for member in members:
            person_data = {
                'member_id': member.get('@Member_Id'),
                'dods_id': member.get('@Dods_Id'),
                'pims_id': member.get('@Pims_Id'),
                'name': member.get('DisplayAs'),
                'interests': []
            }
            
            interests_container = member.get('Interests', {})
            if not interests_container:
                continue
                
            categories = interests_container.get('Category', [])
            if isinstance(categories, dict):
                categories = [categories]
                
            for category in categories:
                cat_name = category.get('@Name')
                cat_id = category.get('@Id')
                
                interests = category.get('Interest', [])
                if isinstance(interests, dict):
                    interests = [interests]
                    
                for interest in interests:
                    interest_data = {
                        'category_name': cat_name,
                        'category_id': cat_id,
                        'interest_id': interest.get('@Id'),
                        'registered_interest': interest.get('RegisteredInterest'),
                        'created': interest.get('Created'),
                        'last_amendment': interest.get('@LastAmendment')
                    }
                    person_data['interests'].append(interest_data)
            
            results.append(person_data)
        
        return results
