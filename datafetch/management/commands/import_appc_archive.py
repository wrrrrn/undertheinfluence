import json
import os
import glob
from os.path import join
from django.core.management.base import BaseCommand
from datafetch import helpers
from datafetch.services.appc_parser import AppcPDFParser

class Command(BaseCommand):
    help = 'Import historical PRCA professional lobbying registers from PDF files.'

    def add_arguments(self, parser):
        parser.add_argument('--refresh', action='store_true', help='Refresh downloaded files')
        parser.add_argument('--file', type=str, help='Path to a specific PDF file to process (for debugging)')

    def handle(self, *args, **options):
        self.refresh = options.get('refresh', False)
        target_file = options.get('file')
        
        archive_path = "appc_archive"
        helpers.create_data_folder(archive_path)

        parser = AppcPDFParser()

        if target_file:
            self._process_single_file(target_file, parser, archive_path)
        else:
            self._process_all_files(parser, archive_path)

    def _process_single_file(self, target_file, parser, archive_path):
        self.stdout.write(f"Analyzing specific PDF: {target_file}")
        try:
            # If it's a URL, download it first
            if target_file.startswith("http"):
                pdf_filename = target_file.split('/')[-1].split('?')[0]
                helpers.fetch_file(target_file, pdf_filename, path=archive_path, refresh=self.refresh)
                pdf_filepath = join('data', archive_path, pdf_filename)
            else:
                pdf_filepath = target_file

            companies_data = parser.parse(pdf_filepath, target_file)
            self.stdout.write(self.style.SUCCESS(f"  - Extracted {len(companies_data)} companies from {target_file}"))

            # For debugging, print the first few results
            if companies_data:
                self.stdout.write("\n--- Sample Extracted Data (First 3) ---")
                for company in companies_data[:3]:
                    self.stdout.write(json.dumps(company, indent=2))
        
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Failed to process {target_file}: {e}"))

    def _process_all_files(self, parser, archive_path):
        self.stdout.write("Processing all PDFs in archive...")
        
        # In a real scenario, we'd fetch the list of files to download first, 
        # but for now we'll assume they are downloaded or just process what's there.
        # Ideally, we should reuse the scraping logic to ensure we have all files.
        # For this step, let's just process the local files.
        
        pdf_files = glob.glob(join('data', archive_path, "*.pdf"))
        
        if not pdf_files:
            self.stdout.write(self.style.WARNING(f"No PDF files found in data/{archive_path}."))
            return

        total_companies = 0
        successful_files = 0
        failed_files = 0

        for pdf_path in sorted(pdf_files):
            filename = os.path.basename(pdf_path)
            self.stdout.write(f"\nProcessing {filename}...")
            try:
                companies_data = parser.parse(pdf_path, filename)
                count = len(companies_data)
                self.stdout.write(self.style.SUCCESS(f"  - Extracted {count} companies"))
                total_companies += count
                successful_files += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"  - Failed: {e}"))
                failed_files += 1
        
        self.stdout.write("\n" + "*"*40)
        self.stdout.write(f"SUMMARY")
        self.stdout.write(f"Processed {successful_files} files successfully.")
        self.stdout.write(f"Failed {failed_files} files.")
        self.stdout.write(f"Total companies extracted: {total_companies}")
        self.stdout.write("*"*40)