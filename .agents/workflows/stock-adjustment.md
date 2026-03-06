---
description: How to use the Stock Adjustment feature
---

# Stock Adjustment Workflow

## Overview
The Stock Adjustment feature allows operators to manually correct ingredient stock levels (`remain_vol`) in the system. This is used for physical count corrections, damage write-offs, transfers, or any situation where the actual stock doesn't match the system.

## Step-by-Step Workflow

### 1. Navigate to Stock Adjustment
- Go to **PRODUCTION PLAN** page
- Click the **"📦 Stock Adjustment"** tab (next to "Production Plans")

### 2. Look Up the Lot
- In the **"Lot ID"** field, enter the `intake_lot_id` of the ingredient lot you want to adjust
- Press **Enter** or click the **🔍** search icon
- The system will auto-fill:
  - **Material**: SAP code and description
  - **Current Stock**: Current `remain_vol` in kg

### 3. Fill the Adjustment Form
- **Type**: Toggle between:
  - `↑ Increase` — adds stock (e.g., receiving correction, transfer in)
  - `↓ Decrease` — removes stock (e.g., spillage, expired, quality rejection)
- **Quantity (kg)**: Enter the adjustment amount (always positive)
- **Reason**: Select from predefined reasons:
  - Physical Count
  - Spillage / Damage
  - Expired Write-off
  - Quality Rejection
  - Receiving Correction
  - Transfer In
  - Transfer Out
  - Other
- **Remark**: (Optional) Free-text notes for context
- **Adjusted By**: Operator name

### 4. Submit
- Click **"✓ Submit Adjustment"**
- If the decrease is >20% of current stock, a confirmation warning dialog will appear
- On success, the form resets and the history table refreshes

### 5. Review History
- The **Adjustment History** table shows all past adjustments
- Each row shows: before/after volumes, type (green ↑ / red ↓), reason, and operator
- Use the **per-column filter** row (🔍 icons) to search/filter the history
- Click the **↻ refresh** button to reload the latest data

## Safety Features
- **Cannot decrease below 0**: System will reject if `adjust_qty > remain_vol`
- **Large adjustment warning**: Popup confirmation for decreases >20% of current stock  
- **Atomic update**: `remain_vol` and adjustment record are saved in a single DB transaction
- **Immutable audit trail**: Every adjustment is permanently recorded

## API Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/stock-adjustments/` | List all adjustments |
| `POST` | `/stock-adjustments/` | Create new adjustment |
| `GET`  | `/stock-adjustments/lot-lookup/{lot_id}` | Look up lot info |
| `GET`  | `/stock-adjustments/lot-search?q=...` | Search lots |

## Files Modified
- `models.py` — `StockAdjustment` model (table: `stock_adjustments`)
- `schemas.py` — `StockAdjustmentCreate`, `StockAdjustment`, `LotLookup`
- `routers/router_stock_adjustments.py` — API router
- `routers/__init__.py` — Router registration
- `main.py` — Router inclusion
- `x30-ProductionPlan.vue` — Frontend tab + form + history table
