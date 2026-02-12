# xMixing System: End-to-End Workflow & Acceptance Test Protocol

This document serves as the definitive guide for the **xMixing** application workflows, specifically tailored for the Pre-Batch and Production ecosystem. It details the technical interactions between the Frontend (Nuxt), Backend (FastAPI), and physical hardware (Scales).

---

## 1. System Architecture & Prerequisites

### Technical Stack
*   **Frontend**: Nuxt.js (Vue 3) running on Port `3000`.
*   **Backend**: FastAPI (Python) running on Port `8000`.
*   **Database**: SQL Database (e.g., SQLite/PostgreSQL) with `SQLAlchemy` ORM.
*   **IoT/Hardware**: MQTT Broker (Port `1883`) handling Scale data `{"scale_id": "...", "weight": "..."}`.
*   **Printing**: Browser-based print dialog (supports Zebra/Brother via system print).

### Terminology
*   **SKU**: Stock Keeping Unit (The Recipe).
*   **Plan**: Production Plan (Ordering a quantity of SKU).
*   **Batch**: A sub-unit of a Plan (e.g., Plan=1000kg, Batch=500kg x 2).
*   **PBTask (PreBatch Task)**: A specific instruction to weigh 1 ingredient for 1 batch.
*   **PBLog (PreBatch Log)**: The historical record of a completed weighing action.

---

## 2. Core Workflows

### Module A: Master Data Setup (Admin/Manager)
**Objective**: Define *what* can be produced.

1.  **Ingredient Creation**:
    *   **Data**: `Ingredient` table.
    *   **Action**: Create generic ingredients (e.g., "Sugar", "Salt").
    *   **Key Field**: `std_package_size` (Default package size for weighing).
2.  **SKU (Recipe) Design**:
    *   **Data**: `Sku` + `SkuStep` tables.
    *   **Action**: Create a Recipe (e.g., "Syrup Type A").
    *   **Step Definition**: Add steps with `re_code` (Ingredient ID) and `require` (Amount per Std Batch).
    *   **Validation**: Ensure `std_batch_size` (e.g., 1000kg) is set on SKU Master.

### Module B: Inventory & Intake (Store)
**Objective**: Bring physical stock into the system.

1.  **Intake Process**:
    *   **Action**: Store operator scans Supplier Lot.
    *   **System**: Creates `IngredientIntakeList` record.
    *   **Key Data**: `intake_lot_id` (Internal Traceability ID), `expire_date`.
2.  **Labeling**:
    *   **Output**: 6x6cm Label with QR Code containing `intake_lot_id`.

### Module C: Production Planning (Planner)
**Objective**: Schedule production.

1.  **Plan Creation**:
    *   **Input**: SKU, Total Volume, Batch Size.
    *   **System Action**: Calculates number of batches.
    *   **DB Entry**: Creates `ProductionPlan` and child `ProductionBatch` records.
    *   **Status**: `Created` -> `Released`.
    *   *Note*: Task lists (`PBTask`) are **NOT** created yet. They are "Lazy Loaded".

### Module D: Pre-Batch Execution (Operator)
**Objective**: The core weighing workflow.

**Step 1: Job Selection**
*   **User**: Navigates to `x40-PreBatch`. Selects a **Plan** -> Selects a **Batch**.
*   **System (Backend)**:
    *   Receives `GET /pb-tasks/{batch_id}`.
    *   **Auto-Provisioning**: Checks if `PBTask` records exist for this batch.
    *   If missing, it reads the `SkuStep` table and generates `PBTask` records for every ingredient.
    *   Returns the list of tasks to the UI.
*   **UI Status**: Ingredients appear with Status `0` (Pending/Grey).

**Step 2: Weighing Setup**
*   **User**: Clicks an Ingredient (e.g., "Sugar").
*   **System**:
    *   Updates `PBTask` status to `1` (In-Progress/Orange) via `PUT /pb-tasks/.../status`.
    *   **Inventory Logic**: Suggests the **oldest active lot** (FIFO) from `IngredientIntakeList`.
*   **User**: Scans/Selects the suggested `intake_lot_id`.

**Step 3: Physical Weighing**
*   **Hardware**: Scale sends MQTT message `topic: scale` -> `{"scale_id": "scale-01", "weight": "25.05"}`.
*   **Frontend**:
    *   Subscribes to `scale` topic.
    *   Updates "Actual Scale Value" in real-time.
    *   Compares with Target Weight. Shows **Green** if within tolerance, **Yellow/Red** if not.

**Step 4: Completion & Labeling**
*   **User**: Clicks "Done" / "Print".
*   **System (Transaction)**:
    1.  **POST `/pb-logs/`**: Saves `PBLog` (Weight, Lot ID, Timestamp).
    2.  **Logic**: Checks if `Total Packages` matched.
    3.  **If Complete**: Calls `PUT /pb-tasks/.../updated status=2` (Complete/Green).
*   **Output**: Prints "Pre-Batch Label" (QR: `batch_id` + `re_code`).

---

## 3. Acceptance Test Checklist (UAT)

Use this checklist to validate the system before deployment.

| Cat | ID | Test Scenario | Steps to Execute | Expected Outcome | Result |
|:---:|:---|:---|:---|:---|:---:|
| **Sys** | **T01** | **Task Auto-Provisioning** | 1. Create new Plan/Batch.<br>2. Open `PreBatch` screen.<br>3. Select Batch. | Ingredient list appears immediately. Backend logs show "Creating tasks...". | |
| **Sys** | **T02** | **Task Persistence** | 1. Reload the page.<br>2. Select same Batch. | List appears identical. Backend logs "Tasks already exist" (No duplication). | |
| **Op** | **T03** | **FIFO Validation** | 1. Have Inventory Lot A (Exp: Jan) & Lot B (Exp: Feb).<br>2. Select Ingredient.<br>3. Try to scan Lot B. | System warns "FIFO Violation". Suggests Lot A. | |
| **IoT** | **T04** | **Scale Integration** | 1. Connect MQTT.<br>2. Send `{"scale_id":"scale-01", "weight": "10.0"}`. | UI Scale 1 Card shows "10.0000". Updates smoothly. | |
| **Op** | **T05** | **Tolerance Check** | 1. Target: 10kg, Tol: 0.1kg.<br>2. Scale: 9.5kg.<br>3. Scale: 10.05kg. | 9.5kg = Yellow/Red background.<br>10.05kg = Green background. | |
| **Data**| **T06** | **Logging & History** | 1. Complete a weigh.<br>2. Check "PreBatch List" table. | Row appears with correct Weight, Lot ID, and timestamp. | |
| **Data**| **T07** | **Status Flow** | 1. Observe Ingredient Status.<br>2. Click Ingredient.<br>3. Complete Weighing. | Status: Grey (0) -> Orange (1) -> Green (2). | |
| **Out** | **T08** | **Label Generation** | 1. Click "Print" on completion. | Dialog opens. QR scans as: `PlanID|BatchID|IngID|Weight` (or configured format). | |
| **Err** | **T09** | **Network Resilience** | 1. Disconnect MQTT.<br>2. Reconnect. | UI notifies disconnection. Auto-reconnects and resumes updating. | |

---

## 4. Maintenance & Troubleshooting

### Database Reset & Sync
*   **Script**: `sync_pb.py`
    *   **Function**: **DESTRUCTIVE**. Drops `pb_tasks`, `pb_logs`, `prebatch_records` and recreates empty tables.
    *   **Use Case**: Only use during initial development or corrupted schema states. **NEVER** runs in production without backup.

### API Endpoints for Support
If the UI behaves unexpectedly, check these endpoints:
1.  **Check Tasks**: `GET /pb-tasks/{batch_id}` - Are tasks Status 0, 1, or 2?
2.  **Check Logs**: `GET /prebatch-records/by-plan/{plan_id}` - Is the history saved?

### Common Issues
*   **"No Ingredients Found"**: Ensure the SKU linked to the Plan has `SkuStep` entries defined.
*   **"Scale Not Moving"**: Check MQTT Broker connection (Port 1883). Ensure Topic is `scale`.
*   **"FIFO Violation"**: Ensure Inventory Intake has valid `expire_date`.

---
*Document Revision: 1.1 - Updated for `PBTask` Architecture*
