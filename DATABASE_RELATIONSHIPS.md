# Database Relationships & Schema Documentation

Results from the analysis of `models.py`.

## Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    %% --- MASTER DATA ---
    INGREDIENTS ||--o{ INGREDIENT_INTAKE_LISTS : "stocked as"
    INGREDIENTS {
        int id PK
        string re_code uk "Unique Reference Code"
        string mat_sap_code "SAP Material Code"
        string name
        float std_package_size
    }

    SKU_MASTERS ||--|{ SKU_STEPS : "consists of"
    SKU_MASTERS {
        string sku_id PK "Recipe ID"
        string sku_name
        float std_batch_size
    }

    SKU_STEPS {
        int id PK
        string sku_id FK
        string re_code FK "Links to Ingredient"
        float require "Qty per Batch"
        int sub_step "Sequence"
    }

    %% --- INVENTORY ---
    INGREDIENT_INTAKE_LISTS ||--o{ PB_LOGS : "consumed by"
    INGREDIENT_INTAKE_LISTS {
        string intake_lot_id PK "Internal Lot ID"
        string lot_id "Supplier Lot"
        string re_code FK
        float remain_vol "Current Stock"
        datetime expire_date
    }

    %% --- PLANNING ---
    PRODUCTION_PLANS ||--|{ PRODUCTION_BATCHES : "split into"
    PRODUCTION_PLANS {
        string plan_id PK
        string sku_id FK
        float total_volume
        int num_batches
    }

    PRODUCTION_BATCHES ||--|{ PB_TASKS : "generates tasks"
    PRODUCTION_BATCHES {
        string batch_id PK
        string plan_id FK
        float batch_size
    }

    %% --- EXECUTION (Pre-Batch) ---
    PB_TASKS ||--|{ PB_LOGS : "logged execution"
    PB_TASKS {
        int id PK
        string batch_id FK
        string re_code FK
        float required_volume "Target Weight"
        enum status "0=Pending, 1=Doing, 2=Done"
    }

    PB_LOGS {
        int id PK
        int task_id FK
        string intake_lot_id FK "Source Lot"
        float net_volume "Actual Weight"
        datetime created_at
    }
```

## Key Relationship Flows

### 1. The "Recipe" Flow (Master Data)
*   **SKU Master** (`SKU_MASTERS`) defines the header of a product (e.g., "Syrup Type A").
*   It has multiple **SKU Steps** (`SKU_STEPS`).
*   Each step referencing an ingredient links via `re_code` (Reference Code) to the **Ingredient** table. This is a soft link in some systems but critical for looking up names and standard package sizes.

### 2. The "Stock" Flow (Inventory)
*   Raw materials enter via **Ingredient Intake** (`INGREDIENT_INTAKE_LISTS`).
*   Key Traceability Field: `intake_lot_id`. This ID is printed on the QR label of the raw material bag.
*   **Relationship**: When a pre-batch action is performed, the system records which `intake_lot_id` was used in `PB_LOGS`.

### 3. The "Work Order" Flow (Planning)
*   A **Production Plan** (`PRODUCTION_PLANS`) requests a total volume (e.g., 1000kg).
*   This is divided into **Production Batches** (`PRODUCTION_BATCHES`) based on the `std_batch_size` vs `batch_size`.
    *   *Example*: 1000kg Plan / 500kg Batch Size = 2 Batches.
*   The system (via the new logic) generates **PB Tasks** (`PB_TASKS`) for each batch.
    *   One Task per Ingredient per Batch.

### 4. The "Execution" Flow (Traceability)
*   **PB Task** tells the operator: "Weigh 25kg of Sugar for Batch 001".
*   **PB Log** records the result: "Operator weighed 25.05kg of Sugar using Lot #L-299 at 10:05 AM".
*   **Traceability Chain**:
    `Plan` -> `Batch` -> `Task` -> `Log` -> `Intake Lot` -> `Supplier Lot`.

## Structural Integrity Notes
*   **Foreign Keys**: Explicit foreign keys exist between Plans and Batches.
*   **Soft Keys**: Links between Recipe Steps (`re_code`) and Ingredients are often "soft" (string matching) to allow flexibility, but data consistency must be maintained by the application layer.
