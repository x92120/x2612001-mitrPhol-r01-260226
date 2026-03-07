# xMixing System — Data Flow Diagrams

> Auto-generated from project source code  
> Generated: 2026-03-07

---

## 1. High-Level System Architecture

```mermaid
graph TB
    subgraph Frontend["🖥️ Frontend — Nuxt.js"]
        UI_Login["x80 User Login"]
        UI_Ingredient["x10 Ingredient Intake"]
        UI_IngConfig["x11 Ingredient Config"]
        UI_WhConfig["x12 Warehouse Config"]
        UI_IntakeReport["x13 Intake Report"]
        UI_SKU["x20 SKU / Recipe"]
        UI_Plan["x30 Production Plan"]
        UI_PreBatch["x40 Pre-Batch"]
        UI_Packing["x50 Packing List"]
        UI_Recheck["x60 Batch Recheck"]
        UI_Dashboard["x90 System Dashboard"]
    end

    subgraph Backend["⚙️ Backend — FastAPI"]
        R_Auth["Auth Router"]
        R_Users["Users Router"]
        R_Ingredients["Ingredients Router"]
        R_SKUs["SKUs Router"]
        R_Production["Production Router"]
        R_Plants["Plants Router"]
        R_Warehouses["Warehouses Router"]
        R_StockAdj["Stock Adjustments Router"]
        R_Reports["Reports Router"]
        R_Monitoring["Monitoring Router"]
        R_Views["Views Router"]
        R_Translations["Translations Router"]
    end

    subgraph Database["🗄️ MySQL Database"]
        DB[(xMixing DB)]
    end

    subgraph External["🔌 External Systems"]
        MQTT["Node-RED / RabbitMQ"]
        Scale["Weighing Scales"]
    end

    Frontend -->|"REST API"| Backend
    Backend -->|"SQLAlchemy ORM"| Database
    External -.->|"MQTT / Serial"| Frontend
    Scale -.->|"Weight data"| UI_PreBatch
```

---

## 2. End-to-End Business Process Flow

```mermaid
flowchart LR
    subgraph Phase1["📦 Phase 1: Master Data Setup"]
        A1["Define Ingredients\n(Ingredient Config)"]
        A2["Define Warehouses\n(FH, SPP, MIX)"]
        A3["Define Plants\n(Production Lines)"]
        A4["Create SKU Recipes\n(Steps, Phases, Actions)"]
    end

    subgraph Phase2["📥 Phase 2: Ingredient Intake"]
        B1["Receive Raw Materials"]
        B2["Record Intake Lot\n(Lot ID, SAP Code, Volume)"]
        B3["Weigh Packages\n(Per-Package Weights)"]
        B4["Ingredient Stock\nAvailable"]
    end

    subgraph Phase3["📋 Phase 3: Production Planning"]
        C1["Create Production Plan\n(SKU, Volume, Dates)"]
        C2["Auto-Generate Batches\n(Plan ÷ Batch Size)"]
        C3["Auto-Generate PreBatch\nRequirements per Batch"]
    end

    subgraph Phase4["⚖️ Phase 4: Pre-Batch Weighing"]
        D1["Select Batch & Ingredient"]
        D2["Weigh on Scale\n(Net Volume per Bag)"]
        D3["Deduct from Inventory\n(Intake Lot Stock)"]
        D4["Record PreBatch Bag\n(Bag Barcode, Lot Origin)"]
        D5["Pack Bags into Box"]
    end

    subgraph Phase5["✅ Phase 5: Batch Re-Check"]
        E1["Scan Box Barcode"]
        E2["Scan Each Bag Barcode"]
        E3["Verify Weight vs Target\n(Check Tolerances)"]
        E4{"All Bags OK?"}
        E5["Release to Production"]
        E6["Flag Error Bags"]
    end

    subgraph Phase6["🚚 Phase 6: Delivery & Production"]
        F1["Close Box\n(FH or SPP boxed)"]
        F2["Deliver FH → SPP"]
        F3["Deliver SPP → Production Hall"]
        F4["Mixing Production"]
    end

    Phase1 --> Phase2
    Phase2 --> Phase3
    Phase3 --> Phase4
    Phase4 --> Phase5
    E4 -->|Yes| E5
    E4 -->|No| E6
    E5 --> Phase6
```

---

## 3. Ingredient Intake Data Flow

```mermaid
flowchart TD
    Start(("Ingredient\nArrival")) --> CheckMaster{"Ingredient\nexists in master?"}
    CheckMaster -->|No| CreateIngredient["Create Ingredient\n(ingredient_id, re_code,\nmat_sap_code, name)"]
    CreateIngredient --> CheckMaster
    CheckMaster -->|Yes| CreateIntake["Create Intake Record\n(intake_lot_id, lot_id,\nmat_sap_code, intake_vol)"]

    CreateIntake --> WeighPkgs["Weigh Individual Packages"]
    WeighPkgs --> RecordPkg["Record Package Weight\n(intake_package_receive)"]
    RecordPkg --> MorePkgs{"More\npackages?"}
    MorePkgs -->|Yes| WeighPkgs
    MorePkgs -->|No| StockAvailable(("Stock Available\nremain_vol = intake_vol"))

    subgraph Tables["📊 Tables Written"]
        T1["ingredients"]
        T2["ingredient_intake_lists"]
        T3["intake_package_receive"]
        T4["ingredient_intake_history"]
    end

    CreateIngredient -.-> T1
    CreateIntake -.-> T2
    CreateIntake -.-> T4
    RecordPkg -.-> T3
```

---

## 4. SKU / Recipe Management Data Flow

```mermaid
flowchart TD
    Start(("Recipe\nDesign")) --> CreateGroup["Create SKU Group\n(group_code, group_name)"]
    CreateGroup --> CreateSku["Create SKU Master\n(sku_id, sku_name,\nstd_batch_size)"]
    CreateSku --> DefinePhases["Define Phases\n(Heating, Mixing, Cooling...)"]
    DefinePhases --> AddSteps["Add Recipe Steps\n(phase, action, ingredient,\nrequire, tolerances)"]
    AddSteps --> MoreSteps{"More\nsteps?"}
    MoreSteps -->|Yes| AddSteps
    MoreSteps -->|No| ReviewRecipe["Review Recipe"]
    ReviewRecipe --> DuplicateSku{"Duplicate\nfor variant?"}
    DuplicateSku -->|Yes| CopySku["Duplicate SKU\n(new sku_id, copy all steps)"]
    CopySku --> ReviewRecipe
    DuplicateSku -->|No| ExportExcel["Export to Excel\n(optional)"]

    subgraph Tables["📊 Tables Written"]
        T1["sku_groups"]
        T2["sku_masters"]
        T3["sku_steps"]
        T4["sku_actions"]
        T5["sku_phases"]
        T6["sku_destinations"]
    end

    CreateGroup -.-> T1
    CreateSku -.-> T2
    AddSteps -.-> T3
```

---

## 5. Production Planning Data Flow

```mermaid
flowchart TD
    Start(("Create\nPlan")) --> SelectSku["Select SKU\n(recipe + batch size)"]
    SelectSku --> SetVolume["Set Total Volume\n& Number of Batches"]
    SetVolume --> SetDates["Set Start / Finish Date"]
    SetDates --> SavePlan["Save Production Plan\n(production_plans)"]
    SavePlan --> AutoBatches["Auto-Generate Batches\n(production_batches)\nN batches = total ÷ batch_size"]
    AutoBatches --> AutoReqs["Auto-Generate PreBatch Reqs\n(prebatch_reqs)\nFrom SKU recipe steps"]
    AutoReqs --> SyncWH["Sync Warehouse (wh)\nfrom ingredient master"]
    SyncWH --> PlanReady(("Plan Ready\nfor Pre-Batch"))

    subgraph StatusFlags["📌 Status Tracking"]
        SF1["flavour_house ⬜"]
        SF2["spp ⬜"]
        SF3["batch_prepare ⬜"]
        SF4["ready_to_product ⬜"]
        SF5["production ⬜"]
        SF6["done ⬜"]
    end

    subgraph Tables["📊 Tables Written"]
        T1["production_plans"]
        T2["production_plan_history"]
        T3["production_batches"]
        T4["prebatch_reqs"]
    end

    SavePlan -.-> T1
    SavePlan -.-> T2
    AutoBatches -.-> T3
    AutoReqs -.-> T4
```

---

## 6. Pre-Batch Weighing Data Flow (Core Transaction)

```mermaid
flowchart TD
    Start(("Start Weighing\nStation: FH or SPP")) --> SelectBatch["Select Batch\n(from production plan)"]
    SelectBatch --> SelectIngredient["Select Ingredient\n(from prebatch_reqs)"]
    SelectIngredient --> CheckStock{"Sufficient\nstock in\nintake lots?"}
    CheckStock -->|No| Alert["⚠️ Insufficient Stock"]
    CheckStock -->|Yes| PlaceOnScale["Place on Scale\n(tare → net weight)"]
    PlaceOnScale --> RecordWeight["Capture Weight\nfrom Scale"]

    RecordWeight --> CreateRec["Create PreBatch Record\n(prebatch_recs)"]
    CreateRec --> RecordOrigin["Record Lot Origin\n(prebatch_rec_from)\n intake_lot_id, take_volume"]
    RecordOrigin --> DeductStock["Deduct from Inventory\n(intake_lists.remain_vol -= net)"]
    DeductStock --> GenerateBarcode["Generate Bag Barcode\n(batch_record_id)"]
    GenerateBarcode --> PrintLabel["Print Label 🏷️"]
    PrintLabel --> MoreBags{"More bags\nfor this ingredient?"}
    MoreBags -->|Yes| PlaceOnScale
    MoreBags -->|No| UpdateReqStatus["Update Req Status\n(0→1→2)"]
    UpdateReqStatus --> MoreIngredients{"More\ningredients?"}
    MoreIngredients -->|Yes| SelectIngredient
    MoreIngredients -->|No| PackBox["Pack Bags into Box"]
    PackBox --> CloseBox["Close Box\n(fh_boxed_at / spp_boxed_at)"]
    CloseBox --> BoxReady(("Box Ready\nfor Re-Check"))

    subgraph Tables["📊 Tables Written"]
        T1["prebatch_recs"]
        T2["prebatch_rec_from"]
        T3["ingredient_intake_lists\n(remain_vol updated)"]
        T4["prebatch_reqs\n(status updated)"]
        T5["production_batches\n(boxed_at updated)"]
    end

    CreateRec -.-> T1
    RecordOrigin -.-> T2
    DeductStock -.-> T3
    UpdateReqStatus -.-> T4
    CloseBox -.-> T5
```

---

## 7. Batch Re-Check & Release Flow

```mermaid
flowchart TD
    Start(("Scan Box\nBarcode")) --> LoadBox["Load Box Details\n(all bags + target weights)"]
    LoadBox --> ScanBag["Scan Bag Barcode"]
    ScanBag --> FindBag["Find Bag Record\n(prebatch_recs)"]
    FindBag --> GetTarget["Get Target Weight\n& Tolerance\n(from prebatch_reqs + sku_steps)"]
    GetTarget --> CompareWeight{"| actual - target |\n≤ tolerance ?"}
    CompareWeight -->|"Yes ✅"| MarkOK["recheck_status = 1 (OK)"]
    CompareWeight -->|"No ❌"| MarkError["recheck_status = 2 (Error)"]
    MarkOK --> MoreBags{"More bags\nto scan?"}
    MarkError --> MoreBags
    MoreBags -->|Yes| ScanBag
    MoreBags -->|No| CheckAll{"All bags\nstatus = OK?"}
    CheckAll -->|Yes| ReleaseBatch["Release to Production\n(ready_to_product = true)"]
    CheckAll -->|No| HandleErrors["⚠️ Review Error Bags"]
    ReleaseBatch --> Deliver(("Ready for\nDelivery"))

    subgraph Tables["📊 Tables Read/Written"]
        T1["prebatch_recs\n(recheck_status updated)"]
        T2["prebatch_reqs\n(target volumes)"]
        T3["sku_steps\n(tolerances)"]
        T4["production_batches\n(ready_to_product)"]
    end

    MarkOK -.-> T1
    MarkError -.-> T1
    GetTarget -.-> T2
    GetTarget -.-> T3
    ReleaseBatch -.-> T4
```

---

## 8. Delivery Flow

```mermaid
flowchart LR
    subgraph FH_Station["🏭 Flavour House (FH)"]
        FH1["Weigh FH Ingredients"]
        FH2["Pack FH Box"]
        FH3["Close FH Box\n(fh_boxed_at)"]
    end

    subgraph SPP_Station["🏭 SPP Station"]
        SPP1["Weigh SPP Ingredients"]
        SPP2["Pack SPP Box"]
        SPP3["Close SPP Box\n(spp_boxed_at)"]
    end

    subgraph Delivery["🚚 Delivery"]
        D1["FH → SPP\n(fh_delivered_at)"]
        D2["SPP → Production Hall\n(spp_delivered_at)"]
    end

    subgraph Production["🔧 Mixing Production"]
        P1["Receive Materials"]
        P2["Execute Recipe Steps"]
        P3["Batch Complete\n(done = true)"]
    end

    FH1 --> FH2 --> FH3 --> D1
    SPP1 --> SPP2 --> SPP3 --> D2
    D1 --> P1
    D2 --> P1
    P1 --> P2 --> P3
```

---

## 9. Stock Adjustment Data Flow

```mermaid
flowchart TD
    Start(("Stock\nDiscrepancy")) --> SearchLot["Search Intake Lot\n(by lot_id / SAP code)"]
    SearchLot --> SelectLot["Select Lot\n(auto-fill lot details)"]
    SelectLot --> ChooseType{"Adjustment\nType?"}
    ChooseType -->|Increase| AddQty["Enter Increase Quantity"]
    ChooseType -->|Decrease| SubQty["Enter Decrease Quantity"]
    AddQty --> SetReason["Set Reason & Remark"]
    SubQty --> SetReason
    SetReason --> SaveAdj["Save Stock Adjustment"]
    SaveAdj --> UpdateStock["Atomically Update\nintake_lists.remain_vol"]
    UpdateStock --> AuditLog["Write Audit Record\n(stock_adjustments)"]
    AuditLog --> Done(("Stock\nCorrected"))

    subgraph Tables["📊 Tables Written"]
        T1["stock_adjustments\n(audit trail)"]
        T2["ingredient_intake_lists\n(remain_vol updated)"]
    end

    AuditLog -.-> T1
    UpdateStock -.-> T2
```

---

## 10. Reporting & Traceability Data Flow

```mermaid
flowchart TD
    subgraph Reports["📊 Available Reports"]
        R1["Production Daily Report\n(plans, batches, consumption)"]
        R2["Pre-Batch Summary Report\n(ingredient variance)"]
        R3["Batch Record Report\n(full batch with ingredients)"]
        R4["Packing List Report\n(bags grouped by batch)"]
        R5["Quality Check Report\n(recheck results)"]
        R6["Ingredient Expiry Alert\n(expired / expiring soon)"]
        R7["Traceability Report\n(lot→batch or batch→lot)"]
        R8["Stock Movement Report\n(adjustments + pre-batch usage)"]
        R9["Ingredient Stock Summary\n(by warehouse: FH, SPP)"]
    end

    subgraph DataSources["🗄️ Data Sources"]
        DS1["production_plans"]
        DS2["production_batches"]
        DS3["prebatch_reqs"]
        DS4["prebatch_recs"]
        DS5["prebatch_rec_from"]
        DS6["ingredient_intake_lists"]
        DS7["stock_adjustments"]
        DS8["sku_steps"]
    end

    DS1 --> R1
    DS2 --> R1
    DS3 --> R2
    DS4 --> R2
    DS4 --> R3
    DS4 --> R4
    DS4 --> R5
    DS6 --> R6
    DS5 --> R7
    DS6 --> R7
    DS7 --> R8
    DS4 --> R8
    DS6 --> R9
    DS7 --> R9

    R7 -->|"Forward"| Forward["Lot → Which Batches used it?"]
    R7 -->|"Backward"| Backward["Batch → Which Lots were used?"]
```

---

## 11. Complete System Data Flow (Summary)

```mermaid
flowchart TB
    subgraph MasterData["📖 Master Data"]
        MD1["Ingredients"]
        MD2["SKU Recipes"]
        MD3["Plants"]
        MD4["Warehouses"]
        MD5["Users"]
    end

    subgraph Intake["📥 Intake"]
        IN1["Receive Materials"]
        IN2["Record Lot & Packages"]
    end

    subgraph Planning["📋 Planning"]
        PL1["Create Plan"]
        PL2["Generate Batches"]
        PL3["Generate Requirements"]
    end

    subgraph PreBatch["⚖️ Pre-Batch"]
        PB1["Weigh Ingredients"]
        PB2["Deduct Stock"]
        PB3["Print Labels"]
        PB4["Pack & Close Box"]
    end

    subgraph QC["✅ Re-Check"]
        QC1["Scan & Verify Bags"]
        QC2["Release to Production"]
    end

    subgraph Delivery["🚚 Delivery"]
        DL1["FH → SPP"]
        DL2["SPP → Production Hall"]
    end

    subgraph StockMgmt["📦 Stock Management"]
        SM1["Stock Adjustments"]
        SM2["Movement Tracking"]
    end

    subgraph Reporting["📊 Reporting"]
        RP1["Traceability"]
        RP2["Daily Reports"]
        RP3["Expiry Alerts"]
    end

    MD1 --> IN1
    MD2 --> PL1
    MD3 --> PL1
    MD4 --> IN1

    IN1 --> IN2
    IN2 -->|"Stock available"| PB1

    PL1 --> PL2 --> PL3
    PL3 -->|"Requirements ready"| PB1

    PB1 --> PB2
    PB2 --> PB3
    PB3 --> PB4

    PB4 --> QC1
    QC1 --> QC2

    QC2 --> DL1
    QC2 --> DL2

    IN2 --> SM1
    PB2 --> SM2
    SM1 --> SM2

    IN2 --> RP1
    PB2 --> RP1
    PL1 --> RP2
    IN2 --> RP3
```
