# xMixing System Workflow Summary

Welcome to the **xMixing** project. This system is designed to manage the end-to-end production process of mixed chemical/food products, from raw material intake to final packing.

## 🏗️ System Architecture
- **Frontend**: Nuxt 3 + Quasar Framework (Vue.js)
- **Backend**: FastAPI (Python) + SQLAlchemy
- **Data Stores**: 
    - **MySQL**: Primary relational data (Plans, Batches, Inventory).
    - **InfluxDB**: Time-series history for batch performance monitoring.
- **Hardware Integration**: 
    - **MQTT Bridge**: Python script connecting Serial Scales to the application via RabbitMQ.
    - **Label Printers**: Integrated via browser print services and SVG templates.

---

## 🔄 Business Workflow

### 1. Planning & Master Data
- **SKU Management (`x20-Sku`)**: Define the product catalogue and their recipes.
- **Production Planning (`x30-ProductionPlan`)**:
    - Users select a SKU and target volume.
    - The system automatically calculates the number of **Batches** required based on the selected **Plant's** capacity.
    - Creates `production_plans` and `batches` in the database.

### 2. Material Management
- **Ingredient Intake (`x10-IngredientIntake`)**: 
    - Log incoming raw materials.
    - Assign Lot numbers and generate initial barcodes for tracking.
- **Inventory Tracking**: Managed across various warehouses (`x12`).

### 3. Pre-Batch Process (Weighing)
- **Selection (`x40-PreBatch`)**:
    - Operators select a plan and batch to work on.
    - The system displays the required volume for each ingredient in that batch.
- **Weighing**:
    - Integrated with physical scales through the **MQTT Bridge**.
    - Operators scan the raw material barcode and weigh the exact amount.
    - System records the `net_volume` and generates a **Pre-Batch Record**.

### 4. Quality Control & Packing
- **Batch Recheck (`x60-BatchRecheck`)**:
    - Optional scan step to verify that all ingredients in a physical batch match the plan.
- **Packing List (`x50-PackingList`)**:
    - Final stage of "boxing" the pre-mixed ingredients.
    - **2-Step Verification**: Scan an ingredient bag, then scan the Box ID (Plan/Batch) to confirm it is physically inside.
    - **Label Printing**: Generates and prints a **Batch Box Label** (Manifest) listing all ingredients, total weight, and plan details.

---

## 🛠️ Development & Deployment
- **Startup**: Use `./start-app.sh` to launch Docker (RabbitMQ/Node-Red), the MQTT Bridge, FastAPI Backend, and Nuxt Frontend.
- **Logging**: All logs are redirected to `*.log` files in the root directory for easy troubleshooting.
- **Status Check**: Use `./status-app.sh` to monitor all running services.

---
*Created on 2026-02-16*
