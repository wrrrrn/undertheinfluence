import calendar
from datetime import datetime
from os.path import join
import re
import os
import json
from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

from datafetch import models, helpers


class Command(BaseCommand):
    help = 'Import historical PRCA professional lobbying registers from PDF files.'

    # Keywords to filter out when identifying potential company names in practitioners/clients
    SECTION_KEYWORDS = [
        "Address", "Contact Details", "Practitioners", "Fee-Paying", "Register for",
        "Pages", "www", "http", ".com", ".uk", ".org", "@", "email", "phone", "Ltd", "Group", "Company", "UK", "Consulting",
        "LLP", "Limited", "Partners", "Strategy", "Global", "Communications", "Public"
    ]

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')

    def get_dates_from_pdf_text(self, text):
        # Format: "Register for 1st March 2021 - 31st May 2021"
        months = "|".join(calendar.month_name[1:])
        # make month names case-insensitive
        months = f"(?i:{months})"
        date_range = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+(%s)\s+(\d{4})" % months, text)
        if len(date_range) >= 2:
            start_str = " ".join(date_range[0])
            end_str = " ".join(date_range[1])
            try:
                start_date = datetime.strptime(start_str, "%d %B %Y").date()
                end_date = datetime.strptime(end_str, "%d %B %Y").date()
            except ValueError:
                # Handle cases like "29th February 20" for 2019-2020 which datetime struggles with
                # Try to extract year and reconstruct
                start_year = int(date_range[0][2])
                end_year = int(date_range[1][2])
                if start_year < 100: start_year += 2000 # Assume 20xx
                if end_year < 100: end_year += 2000 # Assume 20xx
                
                start_str = f"{date_range[0][0]} {date_range[0][1]} {start_year}"
                end_str = f"{date_range[1][0]} {date_range[1][1]} {end_year}"
                
                try:
                    start_date = datetime.strptime(start_str, "%d %B %Y").date()
                    end_date = datetime.strptime(end_str, "%d %B %Y").date()
                except ValueError:
                    self.stderr.write(f"Could not parse date from: {start_str} - {end_str}")
                    return None, None
            return str(start_date), str(end_date)
        return None, None

    def _group_blocks_into_companies(self, all_blocks):
        companies_blocks = []
        current_company_blocks = []
        
        # Heuristic: A new company entry starts with a block that is distinct (e.g., larger font, or specific positioning)
        # and is followed by a block containing "Address(es) in the UK".
        # We will iterate through blocks and look for this pattern.

        for i, block in enumerate(all_blocks):
            block_text = block[4].strip()
            if not block_text:
                continue
            
            # --- Filtering out obvious non-company names/headers ---
            if "Register for" in block_text or "Fee-Paying clients" in block_text or \
               "Practitioners" in block_text or "Address(es) in the UK" in block_text or \
               "Contact Details" in block_text or block_text.startswith("Page"):
                if current_company_blocks: # If this is a header in the middle of a company, just add it.
                    current_company_blocks.append(block)
                continue # Skip this block as a potential company start
            
            is_company_start = False
            
            # Heuristic 1: Block text looks like a company name (Title Case or ALL CAPS, not too short)
            if len(block_text) > 3 and (block_text.istitle() or block_text.isupper()) and \
               not any(word.lower() in block_text.lower() for word in self.SECTION_KEYWORDS):
                # Look ahead for "Address(es) in the UK" in nearby blocks
                # This makes it more robust
                found_address_nearby = False
                for j in range(i + 1, min(i + 10, len(all_blocks))): # Check next 10 blocks
                    if "Address(es) in the UK" in all_blocks[j][4]:
                        found_address_nearby = True
                        break
                if found_address_nearby:
                    is_company_start = True
            
            if is_company_start:
                if current_company_blocks: # If we have accumulated blocks for a previous company
                    companies_blocks.append(current_company_blocks)
                current_company_blocks = [block] # Start new company block list
            else:
                current_company_blocks.append(block)
        
        # Add the last company's blocks
        if current_company_blocks:
            companies_blocks.append(current_company_blocks)
        
        return companies_blocks

    def _extract_data_from_company_blocks(self, company_blocks, date_range, source_url):
        data = {
            'name': '',
            'address': [],
            'contact_details': [],
            'practitioners': [],
            'clients': [],
            'source_url': source_url,
            'date_range': date_range,
        }
        
        # We need to process blocks with their coordinates to reconstruct sections correctly
        # This will be more complex than simple line splitting.
        
        # Temporary flat text reconstruction for testing
        reconstructed_company_text = "\n".join([b[4].strip() for b in company_blocks if b[4].strip()])
        lines = reconstructed_company_text.split('\n')
        
        # Assuming the first line in the reconstructed text is the company name for now
        if lines:
            data['name'] = lines[0].strip()
            lines = lines[1:] # Remove name from lines

        current_section = None
        for line in lines:
            line_lower = line.lower()
            if 'address(es) in the uk' in line_lower:
                current_section = 'address'
                continue
            elif 'contact details' in line_lower:
                current_section = 'contact_details'
                continue
            elif 'practitioners (employed' in line_lower:
                current_section = 'practitioners'
                continue
            elif 'fee-paying clients' in line_lower:
                current_section = 'clients'
                continue
            
            if line.strip(): # Only process non-empty lines
                if current_section == 'address':
                    data['address'].append(line.strip())
                elif current_section == 'contact_details':
                    data['contact_details'].append(line.strip())
                elif current_section == 'practitioners':
                    data['practitioners'].append(line.strip())
                elif current_section == 'clients':
                    data['clients'].append(line.strip())
        
        # Cleanup practitioners and clients - remove "(i): http://..." or "(i): https://..." and split multiple names
        cleaned_practitioners = []
        for p_line in data['practitioners']:
            p_line = re.sub(r'\(i\):.*', '', p_line).strip()
            names = re.findall(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*)', p_line)
            cleaned_practitioners.extend([n for n in names if n not in self.SECTION_KEYWORDS and n.lower() not in ['advisory', 'role', 'party', 'officer']]) # Add more common filtering words
        data['practitioners'] = cleaned_practitioners

        cleaned_clients = []
        for c_line in data['clients']:
            c_line = re.sub(r'\(i\):.*', '', c_line).strip()
            clients_on_line = re.split(r'\s{2,}|\s*,\s*', c_line)
            cleaned_clients.extend([cl.strip() for cl in clients_on_line if cl.strip() and not cl.startswith("http") and not cl.startswith("www")])
        data['clients'] = cleaned_clients
        
        return data

    def _parse_pdf(self, pdf_path, source_url):
        all_companies_data = []

        with fitz.open(pdf_path) as doc:
            self.stdout.write(f"  - Parsing {doc.page_count} pages with PyMuPDF blocks...")
            
            if doc.page_count == 0:
                self.stderr.write(self.style.ERROR("PDF has no pages."))
                return []

            # Extract date range from the first page's first block
            first_page = doc.load_page(0)
            first_page_blocks = first_page.get_text("blocks", sort=True)
            
            date_range = (None, None)
            if first_page_blocks:
                # Find the first block that looks like a date range
                for block in first_page_blocks:
                    block_text = block[4].strip()
                    temp_date_range = self.get_dates_from_pdf_text(block_text)
                    if temp_date_range[0]:
                        date_range = temp_date_range
                        break
            
            if not date_range or not date_range[0]:
                self.stderr.write(self.style.WARNING(f"  - Could not determine date range from first block of PDF {pdf_path}"))
                return []
            self.stdout.write(f"  - Register date range: {date_range[0]} to {date_range[1]}")

            # Collect all blocks from all pages
            all_blocks = []
            page_widths = {} # To store page widths for column detection
            for page_num in range(doc.page_count):
                page = doc.load_page(page_num)
                all_blocks.extend(page.get_text("blocks", sort=True))
                page_widths[page_num] = page.rect.width

            # Group blocks into company entries
            companies_blocks = self._group_blocks_into_companies(all_blocks)

            self.stdout.write(f"  - Found {len(companies_blocks)} potential company entries.")

            for company_blocks in companies_blocks:
                company_data = self._extract_data_from_company_blocks(company_blocks, date_range, source_url)
                all_companies_data.append(company_data)
        
        return all_companies_data


    def handle(self, *args, **options):
        self.refresh = options.get('refresh', False)
        archive_path = "appc_archive"
        helpers.create_data_folder(archive_path)

        # --- Developer Note ---
        # This command is a work in progress. The core challenge is reliably parsing the PDF files.
        # The code below is a starting point for testing the parsing of a single PDF file.
        # To test, uncomment the following lines and update the sample_link to the PDF you want to test.
        #
        # sample_link = "https://www.prca.global/system/files/paragraphs/cw_file/2025-10/prca-public-affairs-register-q2-2025.pdf" # Modern, 2-column
        # # sample_link = "https://www.prca.global/system/files/paragraphs/cw_file/2025-05/register-6.pdf" # Older, 1-column
        #
        # self.stdout.write(f"Analyzing sample PDF: {sample_link}")
        # pdf_filename = sample_link.split('/')[-1].split('?')[0]
        #
        # try:
        #     helpers.fetch_file(sample_link, pdf_filename, path=archive_path, refresh=self.refresh)
        #     pdf_filepath = join('data', archive_path, pdf_filename)
        #
        #     companies_data = self._parse_pdf(pdf_filepath, sample_link)
        #     self.stdout.write(f"  - Extracted {len(companies_data)} companies from {sample_link}")
        #
        #     # The extracted data is not yet saved to the database.
        #     # You can print it for inspection:
        #     # import json
        #     # for company in companies_data[:5]:
        #     #     self.stdout.write(json.dumps(company, indent=2))
        #
        # except Exception as e:
        #     self.stderr.write(self.style.ERROR(f"Failed to process {sample_link}: {e}"))

        self.stdout.write(self.style.SUCCESS("This command is a work in progress. See the developer notes in the code for instructions on how to proceed."))


