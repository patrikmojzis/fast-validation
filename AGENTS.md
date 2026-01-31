# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Project Overview

This is a Python package providing shared validation primitives for fast-app and fast-agents. The core components are:
- `Schema`: Pydantic-based models with post-parse rule validation
- `ValidatorRule`: Abstract base class for custom validation rules  
- `ValidationRuleException`: Custom exception for validation failures

## Common Commands

### Venv
- When running python code or installing deps, source env in one line with ur command. it is usually in .venv or venv folder.

### Testing
```bash
pytest                    # Run all tests
pytest tests/test_schema.py  # Run specific test file
```

### Building and Installation
```bash
pip install -e .          # Install in development mode
pip install -e ".[test]"  # Install with test dependencies
```

## Architecture

The validation system uses a two-phase approach:
1. **Pydantic validation**: Standard field validation during model creation
2. **Rule validation**: Custom business logic validation via `Schema.validate()`

### Core Components

- **Schema** (`fast_validation/schema.py`): Base class extending Pydantic's BaseModel with rule validation capability
- **ValidatorRule** (`fast_validation/validation_rule.py`): Abstract interface for validation rules 
- **ValidationRuleException** (`fast_validation/exceptions.py`): Custom exception distinct from Pydantic's ValidationError
- **Path resolution** (`fast_validation/paths.py`): JSONPath-like expression resolver for targeting validation rules

### Validation Flow

Rules are defined in `Schema.Meta.rules` as `Schema.Rule` objects containing:
- `path`: JSONPath expression (e.g., "$.field", "$.items[*].value")
- `validators`: List of `ValidatorRule` instances

The `Schema.validate()` method:
1. Resolves path expressions against model data
2. Applies validators to matched values
3. Collects validation errors
4. Raises `ValidationRuleException` with aggregated errors

### Key Patterns

- Rules operate on the full model data context, not just individual fields
- Path expressions support nested object access and list iteration with `[*]`
- Validation is async to support complex rule logic
- Partial validation available via `validate(partial=True)`