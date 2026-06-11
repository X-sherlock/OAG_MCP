---
name: get-fund-metric-values
description: Retrieve YAML-defined fund metric facts by fund code, period, and metric attribute list. The skill returns fact records with attribute_name, period, value, unit, as_of_date, and source.
---

# get-fund-metric-values

## Skill Contract

| Field | Value |
|---|---|
| skill_id | `get-fund-metric-values` |
| skill_name | Get Fund Metric Values |
| target_object_type | `Fund` |
| provides_fact_types | `metric_value` |
| supported_subject_types | `Fund` |
| supported_constraints | `period` |
| permission_scope | `fund_public_data:read` |

## Purpose

`get-fund-metric-values` retrieves interval-based metric facts for one fund. The upstream OAG node provides the fund code, period, and metric attribute list. The runtime validates the structured input, calls the configured Java platform endpoint, and returns normalized fact records.

## Accepted Input

The runtime accepts a JSON object with three fields:

```json
{
  "fund_code": "000001",
  "period": "1y",
  "attributes": [
    "return_rate",
    "max_drawdown",
    "sharpe_ratio"
  ]
}
```

| Field | Type | Required | Description |
|---|---|---:|---|
| `fund_code` | `string` | yes | Fund code resolved by the upstream OAG node. |
| `period` | `string` | yes | Period constraint for interval metrics. |
| `attributes` | `array[string]` | yes | Metric attributes requested from the supported attribute set. |

The Java request body is built from `fund_code`, `period`, and `attributes`.

## Supported Periods

| Period | Meaning |
|---|---|
| `1w` | Recent 1 week |
| `1m` | Recent 1 month |
| `3m` | Recent 3 months |
| `6m` | Recent 6 months |
| `1y` | Recent 1 year |
| `2y` | Recent 2 years |
| `3y` | Recent 3 years |
| `5y` | Recent 5 years |
| `10y` | Recent 10 years |
| `20y` | Recent 20 years |
| `ytd` | Year to date |
| `si` | Since inception |

## Supported Attributes

| Attribute | Meaning |
|---|---|
| `return_rate` | Interval return rate |
| `annualized_return` | Annualized return |
| `max_drawdown` | Maximum drawdown |
| `volatility` | Volatility |
| `standard_deviation` | Return standard deviation |
| `sharpe_ratio` | Sharpe ratio |
| `sortino_ratio` | Sortino ratio |
| `calmar_ratio` | Calmar ratio |
| `var` | Historical Value at Risk |
| `cvar` | Conditional Value at Risk |
| `downside_risk` | Downside risk |

## Runtime Flow

1. Read JSON input from standard input.
2. Validate `fund_code`, `period`, and `attributes`.
3. Load the Java endpoint from `config.json`.
4. Send an HTTP POST request to the Java platform endpoint.
5. Normalize the Java response into the skill output format.

## Java Endpoint Configuration

`config.json` contains the runtime endpoint and timeout setting:

```json
{
  "timeout_seconds": 15,
  "endpoints": {
    "get-fund-metric-values": "http://java-platform.example.com/api/skill/get-fund-metric-values"
  }
}
```

When the `FUND_API_TOKEN` environment variable is present, the runtime adds it as a bearer token.

## Java Request Body

```json
{
  "fund_code": "000001",
  "period": "1y",
  "attributes": [
    "return_rate",
    "annualized_return",
    "max_drawdown"
  ]
}
```

## Expected Java Response

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "facts": [
      {
        "fact_requirement_id": "req_001",
        "object_type": "Fund",
        "instance_ref": "000001",
        "attribute_name": "return_rate",
        "period": "1y",
        "value": 0.0821,
        "unit": "%",
        "as_of_date": "2026-06-08",
        "source": "dws_fund_perf_metric"
      }
    ],
    "missing_attributes": []
  }
}
```

## Output Fact Schema

Each item in `facts` follows the output fact schema:

| Field | Description |
|---|---|
| `fact_requirement_id` | Fact requirement identifier. |
| `object_type` | Object type, usually `Fund`. |
| `instance_ref` | Fund instance reference, usually fund code. |
| `attribute_name` | Metric attribute name. |
| `period` | Period constraint. |
| `value` | Metric value. |
| `unit` | Metric unit. |
| `as_of_date` | Data as-of date. |
| `source` | Data source identifier. |

## Skill Output

Successful output:

```json
{
  "success": true,
  "message": "success",
  "skill_id": "get-fund-metric-values",
  "input": {
    "fund_code": "000001",
    "period": "1y",
    "attributes": [
      "return_rate",
      "max_drawdown"
    ]
  },
  "facts": [
    {
      "fact_requirement_id": "req_001",
      "object_type": "Fund",
      "instance_ref": "000001",
      "attribute_name": "return_rate",
      "period": "1y",
      "value": 0.0821,
      "unit": "%",
      "as_of_date": "2026-06-08",
      "source": "dws_fund_perf_metric"
    }
  ],
  "missing_attributes": []
}
```

Validation or integration error output:

```json
{
  "success": false,
  "message": "attributes is required and must be a non-empty array",
  "skill_id": "get-fund-metric-values",
  "input": {
    "fund_code": "000001",
    "period": "1y"
  },
  "facts": [],
  "missing_attributes": []
}
```

## OAG Coordination

The upstream OAG node supplies this skill with structured input:

| OAG Result | Skill Input |
|---|---|
| Fund instance code | `fund_code` |
| Period constraint | `period` |
| Metric attributes from ontology recall | `attributes` |

The downstream response node can use `facts` and `missing_attributes` to produce a user-facing answer or report.

## Example

Input:

```json
{
  "fund_code": "000001",
  "period": "1y",
  "attributes": [
    "return_rate",
    "max_drawdown",
    "sharpe_ratio"
  ]
}
```
