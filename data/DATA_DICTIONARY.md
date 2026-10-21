# sample_data.csv - data dictionary

Fully synthetic data produced by `datalab/sample_data.py` (seed 42). It contains no private or real user data.

| Column | Type | Description |
|---|---|---|
| order_id | text | Unique order code (ORD-00001 ...). Excluded from numeric statistics. |
| order_date | date (YYYY-MM-DD) | Order date during 2025. |
| region | category | North, South, East, West. |
| category | category | Electronics, Clothing, Home, Sports, Books. |
| units_sold | integer | Units in the order. |
| unit_price | decimal | Price per unit. |
| discount_pct | integer | Discount percentage (0, 5, 10, 15, 20). |
| revenue | decimal | units x price x (1 - discount/100), computed BEFORE the problems below were injected. |
| customer_age | number | Customer age (18-80). |
| satisfaction_score | decimal | Score from 1.0 to 5.0. |

## Deliberately injected data-quality problems (so validation has something to find)

- 12 exact duplicate rows.
- 15 missing `customer_age`, 10 missing `satisfaction_score`, 5 missing `region`.
- 3 invalid text values in `unit_price` ("abc", "?", "twelve").
- 3 negative `units_sold` values (-1, -2, -3).
- 4 extreme-but-valid `units_sold` values (60, 75, 80, 90) that act as outliers.

Because of the injected problems, `revenue` will not always equal units x price x discount for those rows.
