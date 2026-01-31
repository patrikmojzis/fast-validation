# fast-validation

Async validation rules for Pydantic models that require database checks and complex business logic.

## Overview

`fast-validation` extends Pydantic models with a second validation phase for rules that need access to external resources like databases. While Pydantic handles field-level validation, this library handles cross-field validation and async operations.

## Key Components

- **Schema**: Pydantic model with async rule validation
- **ValidatorRule**: Base class for custom validation rules
- **ValidationRuleException**: Custom exception for validation failures

## Quick Start

```python
from fast_validation import Schema, ValidatorRule, ValidationRuleException

# 1. Create a validation rule
class UserExistsRule(ValidatorRule):
    async def validate(self, *, value, data, loc):
        if not await User.exists(value):
            raise ValidationRuleException(
                f"User {value} not found",
                loc=tuple(loc),
                error_type="user_not_found"
            )

# 2. Define your schema
class UpdateUserRequest(Schema):
    user_id: int
    name: str
    
    class Meta:
        rules = [
            Schema.Rule("$.user_id", [UserExistsRule()])
        ]

# 3. Validate with database checks
request = UpdateUserRequest(user_id=123, name="John")
await request.validate()  # Checks if user 123 exists in database
```

## Database Validation Examples

### Check Record Exists
```python
class ProductExistsRule(ValidatorRule):
    async def validate(self, *, value, data, loc):
        if not await Product.exists(value):
            raise ValidationRuleException(
                f"Product {value} not found",
                loc=tuple(loc),
                error_type="product_not_found"
            )

class UpdateProductRequest(Schema):
    product_id: int
    price: float
    
    class Meta:
        rules = [Schema.Rule("$.product_id", [ProductExistsRule()])]
```

### Validate Unique Constraints
```python
class UniqueEmailRule(ValidatorRule):
    def __init__(self, exclude_id_path=None):
        self.exclude_id_path = exclude_id_path
    
    async def validate(self, *, value, data, loc):
        exclude_id = None
        if self.exclude_id_path:
            exclude_id = data.get(self.exclude_id_path.replace("$.", ""))
        
        if await User.email_exists(value, exclude_id=exclude_id):
            raise ValidationRuleException(
                "Email already exists",
                loc=tuple(loc),
                error_type="duplicate_email"
            )

class CreateUserRequest(Schema):
    email: str
    name: str
    
    class Meta:
        rules = [Schema.Rule("$.email", [UniqueEmailRule()])]

class UpdateUserRequest(Schema):
    id: int
    email: str
    name: str
    
    class Meta:
        rules = [
            Schema.Rule("$.id", [UserExistsRule()]),
            Schema.Rule("$.email", [UniqueEmailRule(exclude_id_path="$.id")])
        ]
```

### Cross-Field Validation
```python
class BalanceSufficientRule(ValidatorRule):
    async def validate(self, *, value, data, loc):
        user_id = data.get("user_id")
        amount = value
        
        balance = await User.get_balance(user_id)
        if balance < amount:
            raise ValidationRuleException(
                f"Insufficient balance. Available: {balance}, Required: {amount}",
                loc=tuple(loc),
                error_type="insufficient_balance"
            )

class TransferRequest(Schema):
    user_id: int
    amount: float
    recipient_id: int
    
    class Meta:
        rules = [
            Schema.Rule("$.user_id", [UserExistsRule()]),
            Schema.Rule("$.recipient_id", [UserExistsRule()]),
            Schema.Rule("$.amount", [BalanceSufficientRule()])
        ]
```

## Path Expressions

Rules target specific fields using JSONPath-like expressions:

- `$.field` - Single field
- `$.nested.field` - Nested field  
- `$.items[*]` - All items in a list
- `$.items[*].field` - Field in each list item

```python
class BulkUpdateRequest(Schema):
    items: list[dict]
    
    class Meta:
        rules = [
            # Validate each item's product_id exists
            Schema.Rule("$.items[*].product_id", [ProductExistsRule()])
        ]

# Usage
request = BulkUpdateRequest(items=[
    {"product_id": 1, "price": 10.99},
    {"product_id": 2, "price": 15.99}
])
await request.validate()  # Checks both product_id values
```

## Error Handling

```python
try:
    await request.validate()
except ValidationRuleException as e:
    print(f"Validation failed: {e.message}")
    if e.errors:
        for error in e.errors:
            print(f"Field {error['loc']}: {error['msg']}")
```

## Installation

```bash
pip install "git+https://github.com/patrikmojzis/fast-validation.git"
```

Requires Python 3.10+ and Pydantic 2.6+.