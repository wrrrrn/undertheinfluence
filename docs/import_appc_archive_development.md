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
