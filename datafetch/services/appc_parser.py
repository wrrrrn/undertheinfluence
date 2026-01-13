import calendar
import re
import logging
from datetime import datetime
import fitz  # PyMuPDF

logger = logging.getLogger(__name__)

class AppcPDFParser:
    """
    Parses PRCA/APPC PDF registers to extract lobbying data.
    """
    
    # Keywords to filter out when identifying potential company names in practitioners/clients
    SECTION_KEYWORDS = [
        "Address", "Contact Details", "Practitioners", "Fee-Paying", "Register for",
        "Pages", "www", "http", ".com", ".uk", ".org", "@", "email", "phone", "Ltd", "Group", "Company", "UK", "Consulting",
        "LLP", "Limited", "Partners", "Strategy", "Global", "Communications", "Public", "Other Countries"
    ]

    def parse(self, pdf_path, source_url):
        """
        Main entry point. Parses a PDF file and returns a list of company data dicts.
        """
        all_companies_data = []

        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            logger.error(f"Failed to open PDF {pdf_path}: {e}")
            return []

        if doc.page_count == 0:
            logger.error(f"PDF {pdf_path} has no pages.")
            return []

        logger.info(f"Parsing {doc.page_count} pages from {pdf_path}")

        # Extract date range from the first page's first block
        date_range = self._extract_date_range(doc)
        if not date_range or not date_range[0]:
            logger.warning(f"Could not determine date range from {pdf_path}")
            return []
        
        logger.info(f"Register date range: {date_range[0]} to {date_range[1]}")

        # Collect all blocks from all pages (using "dict" to get font info)
        all_blocks = []
        for page_num in range(doc.page_count):
            page = doc.load_page(page_num)
            page_dict = page.get_text("dict", sort=True)
            all_blocks.extend(page_dict["blocks"])

        # Group blocks into company entries
        companies_blocks = self._group_blocks_into_companies(all_blocks)
        logger.info(f"Found {len(companies_blocks)} potential company entries.")

        for company_blocks in companies_blocks:
            company_data = self._extract_data_from_company_blocks(company_blocks, date_range, source_url)
            all_companies_data.append(company_data)
        
        doc.close()
        return all_companies_data

    def _get_block_text(self, block):
        """Helper to extract clean text from a block dict."""
        if "lines" not in block:
            return ""
        text_parts = []
        for line in block["lines"]:
            for span in line["spans"]:
                text_parts.append(span["text"])
        return " ".join(text_parts).strip()

    def _extract_date_range(self, doc):
        first_page = doc.load_page(0)
        # Use "blocks" here just for simple text extraction of the first page
        first_page_blocks = first_page.get_text("blocks", sort=True)
        
        if first_page_blocks:
            for block in first_page_blocks:
                block_text = block[4].strip()
                date_range = self._parse_date_string(block_text)
                if date_range[0]:
                    return date_range
        return (None, None)

    def _parse_date_string(self, text):
        # Format: "Register for 1st March 2021 - 31st May 2021"
        months = "|".join(calendar.month_name[1:])
        months = f"(?i:{months})"
        date_range = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+(%s)\s+(\d{4})" % months, text)
        
        if len(date_range) >= 2:
            start_str = " ".join(date_range[0])
            end_str = " ".join(date_range[1])
            
            def parse_fuzzy_date(day_str, month_str, year_str):
                try:
                    # Normal parse
                    return datetime.strptime(f"{day_str} {month_str} {year_str}", "%d %B %Y").date()
                except ValueError:
                    # Handle "31 June" -> "30 June" logic
                    try:
                        day = int(day_str)
                        month_num = datetime.strptime(month_str, "%B").month
                        year = int(year_str)
                        if year < 100: year += 2000 # Handle 2-digit years if they slipped through regex
                        
                        # Get max days in this month
                        _, max_days = calendar.monthrange(year, month_num)
                        clamped_day = min(day, max_days)
                        
                        return datetime(year, month_num, clamped_day).date()
                    except Exception as e:
                        logger.warning(f"Failed to fuzzy parse date {day_str} {month_str} {year_str}: {e}")
                        return None

            # Standardize 2-digit years if regex captured them (regex expects \d{4} but let's be safe)
            # Actually the regex enforces 4 digits so we are mostly safe, but the handling logic below
            # for "29th February 20" relied on manual extraction.
            # Let's just use the robust parser for the regex matches.
            
            start_date = parse_fuzzy_date(date_range[0][0], date_range[0][1], date_range[0][2])
            end_date = parse_fuzzy_date(date_range[1][0], date_range[1][1], date_range[1][2])

            if start_date and end_date:
                return str(start_date), str(end_date)

            # Fallback for "20" year format which regex might miss if looking for 4 digits
            # If the main regex failed, we wouldn't be in this block.
            # So this is just for when the regex matches but datetime fails.
            return None, None
        return None, None

    def _is_company_header(self, block):
        """
        Determines if a block is a company header based on font size and weight.
        Investigation showed:
        - Q2 2025: Company Headers ~13pt Bold. Body ~7pt.
        - Q3 2025: Company Headers ~13.5pt Bold. Section Headers ~10.8pt Bold. Body ~9pt.
        
        New Heuristic: Size > 11.5 AND Bold.
        """
        if "lines" not in block:
            return False
            
        has_large_bold_text = False
        text_content = ""
        
        for line in block["lines"]:
            for span in line["spans"]:
                text_content += span["text"]
                # Check for Size > 11.5 (to exclude 10.8pt section headers) and Bold
                if span["size"] > 11.5 and (span["flags"] & 16):
                    has_large_bold_text = True
        
        if not has_large_bold_text:
            return False
            
        # Additional sanity checks
        clean_text = text_content.strip()
        
        # Explicitly exclude known section headers even if they are large/bold
        # (Just in case some PDF puts "Practitioners" in 14pt)
        for keyword in self.SECTION_KEYWORDS:
            if keyword.lower() == clean_text.lower() or keyword.lower() + ":" == clean_text.lower():
                 return False

        if "Register for" in clean_text or clean_text.startswith("Page"):
            return False
            
        return True

    def _group_blocks_into_companies(self, all_blocks):
        companies_blocks = []
        current_company_blocks = []
        
        for block in all_blocks:
            block_text = self._get_block_text(block)
            if not block_text:
                continue
            
            # --- Filtering out obvious non-company headers ---
            if "Register for" in block_text or block_text.startswith("Page"):
                 # Just skip page headers/footers entirely
                continue
            
            is_company_start = self._is_company_header(block)
            
            if is_company_start:
                if current_company_blocks:
                    companies_blocks.append(current_company_blocks)
                current_company_blocks = [block]
            else:
                current_company_blocks.append(block)
        
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
            'countries': [],
            'source_url': source_url,
            'date_range': date_range,
        }
        
        # Reconstruct text using the helper that handles 'dict' blocks
        reconstructed_company_text = "\n".join([self._get_block_text(b) for b in company_blocks if self._get_block_text(b)])
        lines = reconstructed_company_text.split('\n')
        
        if lines:
            data['name'] = lines[0].strip()
            lines = lines[1:]

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
            elif 'other countries of operation' in line_lower:
                current_section = 'countries'
                continue
            
            if line.strip():
                if current_section == 'address':
                    data['address'].append(line.strip())
                elif current_section == 'contact_details':
                    data['contact_details'].append(line.strip())
                elif current_section == 'practitioners':
                    data['practitioners'].append(line.strip())
                elif current_section == 'clients':
                    data['clients'].append(line.strip())
                elif current_section == 'countries':
                    data['countries'].append(line.strip())
        
        # Cleanup
        data['practitioners'] = self._cleanup_practitioners(data['practitioners'])
        data['clients'] = self._cleanup_clients(data['clients'])
        
        return data

    def _cleanup_practitioners(self, practitioners):
        cleaned = []
        for p_line in practitioners:
            p_line = re.sub(r'\(i\):.*', '', p_line).strip()
            names = re.findall(r'([A-Z][a-z]+(?: [A-Z][a-z]+)*)', p_line)
            cleaned.extend([n for n in names if n not in self.SECTION_KEYWORDS and n.lower() not in ['advisory', 'role', 'party', 'officer']])
        return cleaned

    def _cleanup_clients(self, clients):
        cleaned = []
        for c_line in clients:
            c_line = re.sub(r'\(i\):.*', '', c_line).strip()
            clients_on_line = re.split(r'\s{2,}|\s*,\s*', c_line)
            cleaned.extend([cl.strip() for cl in clients_on_line if cl.strip() and not cl.startswith("http") and not cl.startswith("www")])
        return cleaned