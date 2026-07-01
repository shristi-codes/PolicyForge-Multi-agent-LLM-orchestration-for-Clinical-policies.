# Core Day 2 Pipeline Components

Production-grade implementation of the three core agents for NCD 150.3 policy enforcement.

## Architecture

```
Policy Text (NCD_150.3.txt)
    ↓
[1] EXTRACTOR (src/agents/extractor.py)
    • LLM with structured outputs (OpenAI GPT-4)
    • Pydantic validation
    ↓ PolicyCriteria
[2] COMPILER (src/agents/compiler.py)
    • Convert criteria → executable filter logic
    • Calculate frequency thresholds
    ↓ CompiledEdit
[3] ADJUDICATOR (src/agents/adjudicator.py)
    • Apply logic to 21,521 Part B records
    • Flag outliers with anomaly scores
    ↓ List[FlaggedProvider]
```

## Setup

1. **Set OpenAI API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add: OPENAI_API_KEY=sk-...
   ```

2. **Ensure data is available**:
   ```bash
   python -m src.data_pull  # If not already done
   ```

## Running Individual Components

### Extractor
```bash
source .venv/bin/activate
python -m src.agents.extractor
```

Extracts structured criteria from NCD 150.3:
- `frequency_limit_months`: 23
- `target_hcpcs_codes`: ["77080", "77081"]
- `eligible_conditions`: 5 clinical scenarios
- Cached to `data/policies/NCD_150.3_criteria.json`

### Compiler
```bash
python -m src.agents.compiler
```

Compiles frequency edit logic:
- Expected annual frequency: 12 months / 23 months ≈ 0.52 services/bene
- Threshold: 1.5x expected = 0.78 services/bene/year
- Generates DuckDB filter expression

### Adjudicator
```bash
python -m src.agents.adjudicator
```

Applies edit to 21,521 provider records:
- Loads from `data/cms_partb_sample.parquet`
- Calculates anomaly scores (actual / expected frequency)
- Classifies severity: critical (4x+), high (3x+), medium (2x+), low (1.5x+)
- Returns flagged providers sorted by risk

## Full Pipeline Test

```bash
python test_pipeline.py
```

Runs extract → compile → adjudicate end-to-end and displays:
- Total flagged providers
- Severity distribution
- Top 5 outliers with anomaly scores

## Output Schema

### PolicyCriteria (Extractor output)
```json
{
  "policy_id": "NCD_150.3",
  "frequency_limit_months": 23,
  "target_hcpcs_codes": ["77080", "77081"],
  "eligible_conditions": [...],
  "age_min": null,
  "exclusions": [...]
}
```

### CompiledEdit (Compiler output)
```json
{
  "policy_id": "NCD_150.3",
  "criteria": { ... },
  "filter_logic": "WHERE HCPCS_Cd IN (...) AND ...",
  "threshold_expression": "avg_srvcs_per_bene > 0.7826",
  "description": "Frequency edit for NCD_150.3..."
}
```

### FlaggedProvider (Adjudicator output)
```json
{
  "npi": "1234567890",
  "provider_name": "Smith, John",
  "provider_type": "Diagnostic Radiology",
  "hcpcs_cd": "77080",
  "tot_benes": 500,
  "tot_srvcs": 1200,
  "avg_srvcs_per_bene": 2.4,
  "flag_reason": "Provider billed 1200 services...",
  "anomaly_score": 4.6,
  "severity": "critical"
}
```

## Technical Details

### Extractor Implementation
- **LLM**: OpenAI `gpt-4o-2024-08-06` with structured outputs API
- **Validation**: Pydantic schema enforcement at API level
- **Caching**: Saves extracted criteria to avoid re-extraction
- **Error handling**: ValidationError for schema mismatches

### Compiler Implementation
- **Frequency logic**: `expected_annual = 12 / frequency_months`
- **Threshold**: Configurable multiplier (default 1.5x)
- **Output**: DuckDB-compatible SQL WHERE clause
- **Type safety**: Strongly typed CompiledEdit model

### Adjudicator Implementation
- **Data loading**: DuckDB → typed ProviderUtilization records
- **Filtering**: Applies CMS redaction threshold (≥11 benes)
- **Scoring**: `anomaly_score = actual_freq / expected_freq`
- **Severity tiers**: 
  - Critical: ≥4x expected
  - High: ≥3x expected
  - Medium: ≥2x expected
  - Low: ≥1.5x expected

## Next Steps (Day 3+)

- [ ] Wire agents into LangGraph 6-node orchestration
- [ ] Implement Critic grounding validator with citations
- [ ] Add hybrid RAG retrieval layer
- [ ] Extend to second policy (e.g., colorectal screening)
