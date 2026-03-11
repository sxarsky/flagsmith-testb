# Feature Budget Limits

Track and enforce evaluation limits for feature flags to prevent runaway costs.

## Models

### FeatureBudget
- `feature` - OneToOne relationship to Feature
- `evaluation_limit` - Maximum evaluations allowed per month
- `current_count` - Current evaluation count for this period
- `reset_date` - Date when the counter resets
- `limit_exceeded_action` - Action when limit exceeded ('disable' or 'alert')
- `limit_exceeded` - Boolean flag if limit has been exceeded

## API Endpoints

### Create Budget
```
POST /api/v1/budgets/
{
  "feature": 1,
  "evaluation_limit": 10000,
  "limit_exceeded_action": "alert"
}
```

### Get Budget
```
GET /api/v1/budgets/{id}/
```

### Get Budget Status
```
GET /api/v1/budgets/{id}/status/
```

Returns usage statistics including:
- `usage_percentage` - Percentage of budget used
- `remaining_evaluations` - Evaluations remaining
- `days_until_reset` - Days until monthly reset

### Reset Budget Counter
```
POST /api/v1/budgets/{id}/reset/
```

### List Budgets
```
GET /api/v1/budgets/
GET /api/v1/budgets/?feature_id=1
```

## Usage

1. Create a budget for a feature
2. Budget counter increments automatically on SDK evaluations
3. When limit is exceeded:
   - **disable**: Feature is automatically disabled
   - **alert**: Alert is sent (logging/notification)
4. Counter resets monthly on `reset_date`

## Integration Points

### SDK Evaluation Tracking
Budget increment logic should be added to SDK views:
- `api/sdk/views.py` - Add budget check and increment on flag evaluation

### Required Migration
```bash
python manage.py makemigrations features
python manage.py migrate
```

## Implementation Status

- ✅ FeatureBudget model
- ✅ Serializers (FeatureBudgetSerializer, FeatureBudgetStatusSerializer)
- ✅ ViewSet with CRUD operations
- ✅ Custom actions (reset, status)
- ✅ URLs configuration
- ⏳ SDK integration (requires modification to sdk/views.py)
- ⏳ Database migration (needs to be generated)
- ⏳ Alert/notification system (future enhancement)
