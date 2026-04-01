# Applied AI Builder for DDR Report Generation

## Overview
This repository contains a modular, production-ready Python pipeline designed to automate the creation of Detailed Diagnostic Reports (DDRs). The system ingests standard visual inspection reports alongside thermal imaging PDFs, extracts the raw text and visual assets, utilizes a multimodal Large Language Model (Gemini 1.5 Flash) to synthesize the findings, and programmatically generates a finalized Word document (DOCX) containing cross-referenced, structured observations.

## Architecture
The system is built upon a strict four-phase pipeline to ensure modularity, scalability, and robust error handling.

### Phase 1: Data Ingestion & Asset Extraction
- Relies on `PyMuPDF` and `Pillow`.
- Parses incoming PDFs to extract raw text mappings.
- Extracts embedded images directly from the PDF bytes. It utilizes a custom geometric hash filter to bypass repetitive background vectors and templates, ensuring only relevant inspection photos are saved to local storage.

### Phase 2: Multimodal Structured Extraction (AI Layer)
- Utilizes the `google-genai` SDK.
- Instead of relying on slow network file uploads, this phase employs an optimized PIL-based thumbnail downscaling technique to embed images directly inline as base64 byte objects. This drastically reduces network latency and bypasses strict API rate limits.
- The AI dynamically maps area findings across the text and matches them to the provided visual assets, strictly returning data against a predefined Pydantic JSON schema.

### Phase 3: Data Merging & Logic Engine
- A deterministic Python logic engine validates the AI output.
- Checks physical file paths to ensure no broken images reach the document generator.
- Flattens list arrays into readable prose (unified diagnostic statements).
- Performs programmatic heuristic checks (e.g., verifying that a visual "normal" status does not conflict with a thermal "overheating" status) and flags any contradictions for manual review.

### Phase 4: Document Assembly
- Uses `python-docx` to bind the logical payload into a dynamic physical document.
- Injects area headings, findings, highlighted heuristic conflicts, and rescaled inspection photos into a professionally formatted document.

## Prerequisites
- Python 3.10+
- A valid Google Gemini API Key

## Setup & Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/Cranberry7/Ai-Generalist.git
   cd Ai-Generalist
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Configure your environment variables:
   Copy the example environment file and insert your API key.
   ```bash
   cp .env.example .env
   ```
   Open the `.env` file and replace `YOUR_KEY_HERE` with your actual Google Gemini API Key.

## Usage
To run the entire pipeline end-to-end, simply place your inspection PDFs into the `data/input/` directory and execute:

```bash
python src/main.py --all
```

To run the pipeline on specific files dynamically from the command line:

```bash
python src/main.py --all --visual /path/to/Visual.pdf --thermal /path/to/Thermal.pdf
```

The final generated report will be located at `data/output/Detailed_Diagnostic_Report.docx`.
