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

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true')

    def get_dates_from_pdf_text(self, text):
        # Format: "Register for 1st March 2021 - 31st May 2021"
        months = "|".join(calendar.month_name[1:])
        months = f"(?i:{months})"
        date_range = re.findall(r"(\d{1,2})(?:st|nd|rd|th)?\s+(%s)\s+(\d{4})" % months, text)
        if len(date_range) >= 2:
            start_str = " ".join(date_range[0])
            end_str = " ".join(date_range[1])
            start_date = datetime.strptime(start_str, "%d %B %Y").date()
            end_date = datetime.strptime(end_str, "%d %B %Y").date()
            return str(start_date), str(end_date)
        return None, None

    def _detect_pdf_format(self, doc):
        # Heuristic: check first few pages for a two-column layout
        for page_num in range(min(3, doc.page_count)):
            page = doc.load_page(page_num)
            blocks = page.get_text("blocks", sort=True)
            mid = page.rect.width / 2
            left_cnt = sum(1 for b in blocks if b[0] < mid)
            right_cnt = sum(1 for b in blocks if b[0] >= mid)

            if left_cnt > 5 and right_cnt > 5:
                return 'modern_two_column'
        
        return 'legacy_single_column'

    def _parse_modern_format(self, doc):
        self.stdout.write("  - Parsing with 'modern_two_column' parser...")
        # Placeholder for the advanced parsing logic for this format
        self.stdout.write("  - (Full parsing logic for this format not yet implemented)")

    def _parse_legacy_format(self, doc):
        self.stdout.write("  - Parsing with 'legacy_single_column' parser...")
        # Placeholder for the parsing logic for this format
        self.stdout.write("  - (Full parsing logic for this format not yet implemented)")


    def _parse_pdf(self, pdf_path):
        with fitz.open(pdf_path) as doc:
            self.stdout.write(f"  - Parsing {doc.page_count} pages...")
            
            if doc.page_count == 0:
                self.stderr.write(self.style.ERROR("PDF has no pages."))
                return

            # 1. Detect format
            pdf_format = self._detect_pdf_format(doc)
            self.stdout.write(f"  - Detected format: {pdf_format}")

            # 2. Dispatch to the correct parser
            if pdf_format == 'modern_two_column':
                self._parse_modern_format(doc)
            else:
                self._parse_legacy_format(doc)
            
    def handle(self, *args, **options):
        self.refresh = options.get('refresh', False)
        archive_path = "appc_archive"
        helpers.create_data_folder(archive_path)

        # For demonstration, we'll run the detection on our three sample files
        sample_links = [
            "https://www.prca.global/system/files/paragraphs/cw_file/2025-10/prca-public-affairs-register-q2-2025.pdf", # 2025
            "https://www.prca.global/system/files/paragraphs/cw_file/2025-05/register-6.pdf", # 2022
            "https://www.prca.global/system/files/paragraphs/cw_file/2025-05/PAB-Register-1-June-2019-to-31-August-2019-1-1.pdf" # 2019
        ]
        
        self.stdout.write(f"Analyzing {len(sample_links)} sample PDF files...")

        for link in sample_links:
            self.stdout.write("="*50)
            self.stdout.write(f"Processing PDF: {link}")
            pdf_filename = link.split('/')[-1].split('?')[0]
            
            try:
                helpers.fetch_file(link, pdf_filename, path=archive_path, refresh=self.refresh)
                pdf_filepath = join('data', archive_path, pdf_filename)

                self._parse_pdf(pdf_filepath)
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to process {link}: {e}"))

