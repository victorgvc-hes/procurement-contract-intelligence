# Contributing Guidelines

Thank you for your interest in contributing to this project.

This repository was developed as an end-to-end AI-powered contract intelligence platform for procurement, focused on PDF ingestion, clause extraction, compliance analytics, semantic search, and decision support. Contributions, suggestions, and improvements are welcome.

## How to Contribute

If you would like to contribute, please follow these guidelines:

1. Fork the repository
2. Create a dedicated feature branch
3. Make your changes
4. Test your changes locally
5. Submit a pull request with a clear and concise description

## Contribution Areas

Potential contribution areas include:

- PDF ingestion and text extraction improvements
- LLM prompt engineering and clause extraction enhancements
- schema validation and structured output reliability
- RAG pipeline and retrieval quality improvements
- embedding and vector database optimisation
- compliance engine logic and analytics enhancements
- FastAPI endpoint improvements
- Streamlit dashboard features and usability enhancements
- testing, reproducibility, and project structure improvements
- documentation and usage examples

## Coding Standards

Please follow these basic rules:

- Write clear, readable, and modular Python code
- Prefer reusable functions and source modules over duplicated logic
- Use meaningful names for files, variables, functions, and classes
- Add comments where the logic is not immediately obvious
- Keep ingestion, extraction, compliance, rag, app, and test modules well organized
- Maintain consistency with the existing project structure and naming conventions
- Validate structured outputs carefully when working with LLM-based extraction

## Testing

Before submitting changes, make sure that:

- scripts and application modules run correctly from the project root
- file paths, imports, and environment variables remain consistent
- outputs are reproducible where applicable
- no sensitive keys, local environment files, or unnecessary artifacts are committed
- relevant documentation is updated
- changes do not break the ingestion, extraction, RAG, compliance, dashboard, or API workflow
- tests pass successfully using `pytest tests/ -v`

## Data Usage

This project uses contract and operational datasets for experimentation and simulation, including the CUAD dataset and SCMS delivery history data.

Due to licensing, privacy, and repository size considerations:

- raw source files should not be committed unless explicitly intended
- generated outputs, cached files, and large artifacts should not be pushed unnecessarily
- contributors should avoid uploading confidential or proprietary contract data
- any sample data used for testing should be safe, non-sensitive, and appropriately documented
- contributors should follow the setup and usage instructions provided in the README

## Project Scope

This repository is primarily focused on:

- contract PDF ingestion and parsing
- LLM-based clause extraction
- schema-validated structured outputs
- compliance monitoring against purchase orders
- RAG-based semantic search and question answering
- procurement analytics, dashboarding, and API integration

Please keep contributions aligned with the core purpose of the project.

## Pull Request Notes

When opening a pull request, please include:

- a short summary of the change
- why the change improves the project
- any impact on extraction quality, retrieval quality, compliance outputs, dashboard behaviour, or API responses
- any new dependencies, assumptions, environment variables, or setup steps

## Questions or Suggestions

If you would like to suggest an improvement, feel free to open an issue or submit a pull request.