# Development of the `import_appc_archive` Command

## 1. Objective

The `import_appc_archive` management command was created to parse historical data from the Public Relations and Communications Association (PRCA) professional lobbying registers. These registers, from 2019 to 2025, are available as a collection of PDF files with varying formats.

The ultimate goal is to extract the following information for each company in each register and save it to the database:

*   Company Name
*   Address
*   Contact Details (Phone, Email, Website)
*   A list of registered Practitioners
*   A list of fee-paying Clients
*   The date range for which the register is valid

## 2. Technical Approach & Libraries

The primary challenge is the inconsistent and semi-structured nature of the PDF files. To address this, we chose the **`PyMuPDF`** (`fitz`) library. It was selected over other libraries like `pdfplumber` because of its superior ability to extract text blocks along with their exact coordinates on the page. This low-level control is essential for programmatically understanding the layout of the documents.

The import process is structured as follows:

1.  **Fetch Links**: Scrape the [PRCA Previous Registers page](https://www.prca.global/sspx/public-affairs-register-previous-registers) to get a list of all historical PDF files.
2.  **Download PDFs**: Download each PDF file into the `data/appc_archive` directory.
3.  **Parse PDFs**: For each PDF, open it with `PyMuPDF`.
4.  **Extract Data**:
    *   Determine the register's date range.
    *   Extract all text blocks from every page.
    *   Group these blocks into logical entries corresponding to individual companies.
    *   Parse the data (address, practitioners, clients) from each company's block group.
5.  **Save Data**: Save the structured data into the Django database models (this part is not yet implemented).

## 3. Development Journey & Strategies

Several strategies were attempted to parse the PDF content.

### 3.1. Initial Text Extraction (Success)

The first step was to get clean text from the PDFs. While a simple text extraction is possible, the documents use multi-column layouts.

*   **Strategy**: Assume a two-column layout. For each page, use `PyMuPDF` to get all text blocks with coordinates. Separate blocks into a "left column" and "right column" based on their x-coordinate (e.g., if `block.x1` is less than half the page width).
*   **Fallback**: After reconstructing the text for both columns, check if the right column is mostly empty. If it is, this indicates a single-column layout, and we can concatenate the text from both columns to restore the correct reading order.
*   **Outcome**: This strategy was highly effective at reconstructing a coherent, linear text stream from each page, regardless of the PDF's column layout.

### 3.2. Company Boundary Detection (The Core Challenge)

With a clean text stream, the next challenge was to split the entire document into chunks, where each chunk represents one company's entry.

#### Attempt 1: Regex Splitting (Failure)

*   **Strategy**: Join the text from all pages and use a regular expression to split the document. The assumption was that each company's entry starts with a company name, which is typically in title case or all caps. The regex `\n([A-Z][A-Za-z &'-]+(?:\sLtd)?)` was used to find these names.
*   **Outcome**: This was highly unreliable. Many things that were not company names were matched (e.g., section headers, people's names), and many company names were missed, especially those that were not in a consistent case.

#### Attempt 2: Block-Based Heuristics (Partial Success, Current Implementation)

*   **Strategy**: Instead of working with a flat text stream, work with the list of text blocks directly from `PyMuPDF`. Develop a set of rules (`heuristics`) to decide if a given block is the start of a new company entry.
*   **Current Heuristic**: A block is considered a "company start" if:
    1.  It is not a known header (like "Practitioners" or "Contact Details").
    2.  The text is in title case or all caps.
    3.  Crucially, it is followed within the next 10 blocks by a block containing the text "Address(es) in the UK". This "look-ahead" logic is the most reliable part of the heuristic.
*   **Outcome**: This is a significant improvement over the regex approach. It correctly identifies many company entries. However, it is still not perfect and makes many mistakes, leading to thousands of incorrectly identified "companies." Many practitioners' names or other text snippets are still being misidentified as company names.

### 3.3. Data Extraction from Company Blocks (Needs Improvement)

Once a set of blocks is identified as belonging to a single company, the data within those blocks needs to be parsed.

*   **Strategy**: A simple state machine approach. The code iterates through the lines of text within the company block. When it sees a line containing "Address(es) in the UK", it switches the `current_section` to `'address'`. When it sees "Contact Details", it switches to `'contact_details'`, and so on. All subsequent lines are appended to the current section.
*   **Outcome**: This is a very basic implementation and struggles with the messy, multi-line nature of the data, especially for practitioners and clients which are often listed in multiple columns *within* the main column. The extraction logic is functional but highly error-prone due to its simplicity.

## 4. Current Status & Next Steps

The command is functional but not yet reliable enough for production use. It successfully downloads all PDFs and extracts a large volume of data, but the data quality is low due to parsing inaccuracies.

**What Works:**
*   Discovering and downloading all 26 historical PDF registers.
*   Using `PyMuPDF` to extract text blocks with coordinates.
*   Robustly determining the date range for most registers.

**What Doesn't Work / Main Blockers:**
1.  **Invalid Dates**: The date parsing function `get_dates_from_pdf_text` fails on invalid dates found in some PDFs (e.g., "31 June"). It needs to be made more resilient.
2.  **Company Splitting**: The `_group_blocks_into_companies` function is the biggest weakness. The current heuristic is not sophisticated enough to handle the variety in document structure.
3.  **Data Extraction**: The `_extract_data_from_company_blocks` function is too simplistic. It doesn't correctly parse multi-column lists of practitioners and clients and misinterprets many data points.

### Recommended Next Steps for a Developer

This task has moved from a straightforward engineering task to a complex data science and parsing problem requiring iterative development and experimentation.

1.  **Focus on `_group_blocks_into_companies`**: This is the most critical part.
    *   **Refine the Heuristic**: The current rule is a good start, but it needs to be expanded. Consider using more features of the text blocks from `PyMuPDF`, such as:
        *   **Font Size and Weight**: Company names are often in a larger or bolder font than the surrounding text.
        *   **Y-Coordinate (`block.y0`)**: A new company entry might correspond to a significant "jump" down the page.
        *   **Block Width**: Company names might span the full width of a column.
    *   **Develop a Scoring System**: Instead of a simple `True/False`, each block could be given a "company start score". Blocks with a high score are likely company names.
2.  **Improve `_extract_data_from_company_blocks`**:
    *   **Leverage Coordinates**: Do not just read the text. Use the `x` and `y` coordinates of the blocks to understand the layout *within* a company's entry. This is key to correctly separating multi-column lists of practitioners and clients.
    *   **Section-Specific Parsers**: Create dedicated parsing logic for each section (address, practitioners, clients) that can handle their specific layout quirks.
3.  **Implement Data Saving**: Once the data extraction is reliable, implement the logic to create and save the `Organization`, `Person`, and other related objects to the database.
4.  **Create a Test Suite**: Given the complexity and variability of the PDFs, a small test suite with sample pages from different years would be invaluable for validating changes to the parsing logic without having to run the full import each time.

## 5. Additional Ideas & Recommendations

*   **Visual Debugging**: `PyMuPDF` allows drawing shapes on PDF pages. A very effective debugging technique is to have the script draw red rectangles around detected "Company Start" blocks and green rectangles around "Content" blocks, then save this as a "debug PDF". This allows for instant visual verification of the heuristic's performance.
*   **Font Style Analysis**: Instead of hardcoding font sizes, analyze the distribution of font sizes and names across the document. Identify the "outliers" (larger/bolder) which usually correspond to headers/company names. Access this via `page.get_text("dict")` instead of `"blocks"`.
*   **Intermediate Data Storage**: Separating the *extraction* phase from the *loading* (database) phase is crucial. Save the raw extracted Python dictionaries to JSON files first. This allows developers to work on the database mapping and data cleaning logic without re-running the expensive PDF parsing every time.
*   **Date Parsing Resilience**: For invalid dates like "31 June", implement a "clamping" logic (e.g., set to 30 June) or use a library like `dateutil` which handles fuzzy parsing better than strict `datetime.strptime`.
*   **Fuzzy Matching Validation**: Use the list of known companies from the *current* live register (imported via `import_appc`) as a "dictionary" to validate potential company names found in the historical PDFs. If a block matches a known company name, increase its score.
*   **Structural Clustering**: If heuristics prove too brittle, consider using clustering algorithms (like DBSCAN or K-Means) on the block coordinates (x, y) and font properties to identify visual groups. This can help separate the "sidebar" or "header" content from the main body text without explicit rules.
*   **OCR Fallback**: While `PyMuPDF` works well for text-based PDFs, some older archives might be flattened images or have corrupted text layers. Implement a check: if a page yields no text blocks, fallback to an OCR library (like `tesseract` via `pytesseract`) to extract the content.
*   **Refactoring for Testability**: The `Command` class is becoming monolithic. Move the PDF parsing logic (`_group_blocks_into_companies`, `_extract_data_from_company_blocks`) into a separate service class or utility module. This makes it easier to write unit tests for specific parsing functions using small mock data snippets instead of requiring full PDF files.

## 6. Exploratory Debugging Findings (2026-01-13)

A debug run was performed on the Q2 2025 register (`prca-public-affairs-register-q2-2025.pdf`). The results confirmed significant issues with the **Company Splitting** heuristic (`_group_blocks_into_companies`).

**Key Observations:**
1.  **Merged Companies**: The entry for "3x1" incorrectly absorbed data from the subsequent company "5654 & Company Ltd".
    *   *Evidence*: The contact details for "3x1" included addresses in both Glasgow (correct) and London (belonging to 5654). The practitioners list was unusually long and included names associated with 5654.
    *   *Cause*: The heuristic likely failed to recognize "5654 & Company Ltd" as a new company header, possibly because of the ampersand or digits, treating it instead as content belonging to the previous block.
2.  **Misidentified Companies**: "Indurent" and "Teddy Ryan" were identified as company names.
    *   *Evidence*: "Indurent" appeared as a company but the contact email was `@anacta.co.uk`, suggesting the actual agency was "Anacta". "Teddy Ryan" had no contact details and looked like a practitioner's name.
    *   *Cause*: "Indurent" might have been a client name listed in a way that mimicked a header. "Teddy Ryan" was likely a practitioner name that triggered the "Title Case" rule.
3.  **Data Leakage**: Client names (like "5654 & Company Ltd") sometimes appeared in the client list of the *previous* company, or as a company header themselves.

**Conclusion**: The current look-ahead heuristic ("Address(es) in the UK") is insufficient. It fails when the address block is slightly further away or when other headers mimic the structure. The "Title Case" rule is too broad and captures people and clients as companies. Future work must prioritize a stricter, perhaps coordinate-based or font-style-based, definition of a "Company Header".

## 7. Font Analysis Investigation (2026-01-13)

A script (`inspect_fonts.py`) was run to analyze the font properties of the problematic text blocks in the Q2 2025 register.

**Results:**
*   **Company Headers ("3x1", "5654 & Company Ltd"):**
    *   **Font**: `Arial-BoldMT`
    *   **Size**: `13.02`
    *   **Flags**: `20` (Bold)
*   **Content (Emails, Practitioners, Clients like "Indurent", "Teddy Ryan"):**
    *   **Font**: `ArialMT`
    *   **Size**: `7.01`
    *   **Flags**: `4` (Regular)

**Conclusion:**
There is a **deterministic signal** for company headers: **Font Size > 12** and **Bold**.
*   The previous issue where "5654 & Company Ltd" was merged into "3x1" happened because the parser didn't see the bold/large font and treated it as body text.
*   The misidentification of "Indurent" and "Teddy Ryan" as companies happened because they were Title Case, but they are clearly small/regular font (7.01pt).

**Recommendation:**
Discard the complex "Structural Clustering" approach. Implement a **Font-Based Heuristic**:
1.  Iterate through blocks using `page.get_text("dict")` to access font spans.
2.  A block is a "Company Header" **IF AND ONLY IF** it contains a span with `size > 10` (or specifically ~13pt) and `flags & 16` (Bold).
3.  This simple rule should eliminate 99% of false positives (people/clients) and false negatives (missed headers).

## 8. Implementation & Verification (2026-01-13)

The recommendations were implemented in two steps:
1.  **Refactoring**: The parsing logic was moved from the `Command` class to a new service `datafetch/services/appc_parser.py`.
2.  **Font-Based Heuristic**: The `_group_blocks_into_companies` method was rewritten to use `page.get_text("dict")` and check for **Bold** text larger than **10pt**.

**Verification Results:**
Running the parser against `prca-public-affairs-register-q2-2025.pdf` yielded excellent results:
*   **Total Companies Found**: 86 (previously 193 - the high number was due to false positives).
*   **Split Success**: "3x1" and "5654 & Company Ltd" are now correctly identified as separate companies.
*   **False Positive Removal**:
    *   "Indurent" (a client) is no longer a company. It appears correctly in the client list of "5654 & Company Ltd".
    *   "Teddy Ryan" (a practitioner) is no longer a company. He appears correctly in the practitioner list of "Anacta UK".
*   **Anacta UK**: This company was previously missed or split incorrectly; it is now correctly identified with its practitioners and clients.

**Status:** The parsing logic is now robust for the modern 2-column PDF format. Further testing on older 1-column PDFs (2019-2021) is recommended to ensure the font rules hold up there as well.

## 9. Refining Font Heuristics (2026-01-13)

Testing on `Public_Affairs_Register___Q3_2025%20%282%29_0.pdf` revealed a new challenge:
*   **Issue**: Section headers like "Address(es) in the UK" were **10.8pt Bold**, while Company Headers were **13.5pt Bold**.
*   **Failure**: The initial rule `Size > 10 + Bold` incorrectly flagged section headers as companies, leading to 665 fake companies being extracted.
*   **Resolution**:
    *   Inspected the font hierarchy of the problematic file.
    *   Increased the threshold for Company Headers to **Size > 11.5** + **Bold**.
    *   Added an explicit exclusion for known `SECTION_KEYWORDS` even if they meet the font criteria (defense in depth).
    *   Implemented "fuzzy date parsing" to handle invalid dates like "31 June" (clamped to 30 June).

**Final Result**: The parser now correctly handles both PDF styles, extracting ~73 clean companies from the Q3 register. The bulk import process successfully extracted 2880 companies from 26 files with zero failures.
