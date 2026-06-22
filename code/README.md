# MLE Hiring Challenge Agent

## Setup and Installation

1. Create a Python virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment Variables:
   Copy `.env.example` to `.env` and insert your API keys:
   ```bash
   cp .env.example .env
   # Edit .env and set GROQ_API_KEY
   ```

## Running the Agent

To execute the triage agent against the test set:

```bash
python code/main.py
```

This will read from `support_tickets/support_tickets.csv` and write the predictions to `support_tickets/output.csv`.

## Running Validation

After generating the outputs, validate the CSV structure using the provided script:

```bash
python code/validate_output.py
```

## Running Tests

To execute the deterministic unit tests covering the agent components:

```bash
python -m pytest code/tests -v
```
