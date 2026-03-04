# 📋 xMixing Control System — Handover Testing Document

> **Project:** x2612001-mitrPhol-r02 | **Version:** 0.1  
> **Date:** 2 March 2026  
> **Prepared by:** xDev Team

---

## 📌 Document Overview

This document defines the **Handover Testing Procedure** for the xMixing Control System. It is organized by **Station** and mapped to **Frontend Functions (Pages)** to ensure all features are validated at each physical workstation before project handover.

---

## 🏗️ Station & Equipment Summary

| Station | Station ID | Equipment | Frontend Pages Used |
|---|---|---|---|
| **Server Station** | Server | Server PC, Network | All pages (Dashboard, System Monitor, User Config) |
| **Intake & Prebatch — FH** | FH | PC, Barcode Scanner, Barcode Printer, Weight Scale ×3 | Ingredient Intake, PreBatch, Packing List |
| **Intake & Prebatch — SPP** | SPP | PC, Barcode Scanner, Barcode Printer, Weight Scale ×3 | Ingredient Intake, PreBatch, Packing List |
| **Batch Recheck** | Recheck | PC, Barcode Scanner | Batch Recheck |
| **Mixing Production — Mix_1** | Mix_1 | Barcode Scanner → IOT2050 → PLC | Packing List (scan verify) |
| **Mixing Production — Mix_2** | Mix_2 | Barcode Scanner → IOT2050 → PLC | Packing List (scan verify) |
| **Mixing Production — Mix_3** | Mix_3 | Barcode Scanner → IOT2050 → PLC | Packing List (scan verify) |

---

## 🧪 Testing Status Legend

| Symbol | Meaning |
|---|---|
| ⬜ | Not Tested |
| ✅ | Passed |
| ❌ | Failed |
| ⚠️ | Passed with Issues |
| 🔄 | Re-test Required |
| N/A | Not Applicable |

---

## 1️⃣ Server Station Testing

> **Location:** Server Room / Admin PC  
> **Equipment:** Server PC, Network Infrastructure  
> **Purpose:** System administration, monitoring, and master data configuration

### 1.1 Home / Dashboard (`index.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-01 | Page loads | Navigate to `/` | Dashboard loads with statistics cards | ⬜ | | | |
| S-02 | Dashboard statistics | Login → View home page | Shows Active SKU count, Ingredient Stock, Pending Batches, Active Productions | ⬜ | | | |
| S-03 | Quick access menus | Click each quick access card | Navigates to correct page (SKU, Production Plan, PreBatch) | ⬜ | | | |
| S-04 | System status widget | View system status area | Shows DB status, Uptime, Sync status, Storage info | ⬜ | | | |
| S-05 | Permission-based visibility | Login as Operator vs Admin | Cards only show for permitted features | ⬜ | | | |
| S-06 | Language toggle | Click language flag icon | UI switches between English ↔ Thai correctly | ⬜ | | | |

### 1.2 User Login (`x80-UserLogin.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-10 | Login page loads | Navigate to `/x80-UserLogin` | Login form displays with username/password fields | ⬜ | | | |
| S-11 | Valid login | Enter valid username + password → Login | Redirect to home, success notification | ⬜ | | | |
| S-12 | Invalid login | Enter wrong credentials → Login | Error notification "Invalid credentials" | ⬜ | | | |
| S-13 | Empty fields | Click login with empty fields | Warning notification "fill all fields" | ⬜ | | | |
| S-14 | Navigate to register | Click "Create Account" | Navigates to register page | ⬜ | | | |
| S-15 | Show/hide password | Click eye icon | Password visibility toggles | ⬜ | | | |
| S-16 | Enter key submit | Type credentials + press Enter | Submits login form | ⬜ | | | |

### 1.3 User Registration (`x81-UserRegister.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-20 | Register page loads | Navigate to `/x81-UserRegister` | Registration form displays | ⬜ | | | |
| S-21 | Create new user | Fill all fields → Submit | User created, success notification | ⬜ | | | |
| S-22 | Duplicate username | Register with existing username | Error notification | ⬜ | | | |
| S-23 | Required fields validation | Submit with empty fields | Validation errors shown | ⬜ | | | |

### 1.4 User Configuration (`x89-UserConfig.vue`) — Admin Only

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-30 | User list loads | Navigate to `/x89-UserConfig` | Table with all users displayed | ⬜ | | | |
| S-31 | Search users | Type in search box | Filters users by name/email/role/department | ⬜ | | | |
| S-32 | Create user | Click "Add User" → Fill form → Save | New user appears in table | ⬜ | | | |
| S-33 | Edit user | Click user row → Modify fields → Save | Changes saved, notification shown | ⬜ | | | |
| S-34 | Change role | Edit user → Change role dropdown | Role updated (Admin/Supervisor/Operator) | ⬜ | | | |
| S-35 | Toggle permissions | Edit user → Check/uncheck permissions | Permissions saved correctly | ⬜ | | | |
| S-36 | Deactivate user | Edit user → Set status Inactive | User status changes, cannot login | ⬜ | | | |
| S-37 | Delete user | Click delete → Confirm | User removed from list | ⬜ | | | |

### 1.5 SKU Management (`x20-Sku.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-40 | SKU list loads | Navigate to `/x20-Sku` | SKU master table with all SKUs | ⬜ | | | |
| S-41 | Create new SKU | Click Add → Enter SKU ID, Name, Group → Save | SKU created in database | ⬜ | | | |
| S-42 | Edit SKU | Select SKU → Edit fields → Save | SKU updated | ⬜ | | | |
| S-43 | Add SKU steps | Select SKU → Add Step → Fill phase, action, re_code, require, tolerance → Save | Step added with correct values | ⬜ | | | |
| S-44 | Edit SKU step | Select step → Modify → Save | Step updated | ⬜ | | | |
| S-45 | Delete SKU step | Select step → Delete → Confirm | Step removed | ⬜ | | | |
| S-46 | Duplicate SKU | Click Duplicate → Enter new ID → Save | Full SKU with steps duplicated | ⬜ | | | |
| S-47 | Filter SKUs | Use filter row (by ID, Name, Group) | Table filtered correctly | ⬜ | | | |
| S-48 | Show/Hide inactive | Toggle "Show All" checkbox | Inactive SKUs shown/hidden | ⬜ | | | |
| S-49 | Import CSV | Click Import → Select CSV file | SKU data imported | ⬜ | | | |
| S-50 | Manage Actions | Open Action dialog → CRUD operations | Actions created/edited/deleted | ⬜ | | | |
| S-51 | Manage Phases | Open Phase dialog → CRUD operations | Phases created/edited/deleted | ⬜ | | | |
| S-52 | Manage Groups | Open Group dialog → CRUD operations | Groups created/edited/deleted | ⬜ | | | |
| S-53 | Destination management | Add/edit destinations for steps | Destinations (FH/SPP) saved correctly | ⬜ | | | |
| S-54 | Tolerance settings | Set low_tol / high_tol on step | Tolerance values saved and applied in PreBatch | ⬜ | | | |

### 1.6 Ingredient Configuration (`x11-IngredientConfig.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-60 | Ingredient list loads | Navigate to `/x11-IngredientConfig` | Table with all ingredients | ⬜ | | | |
| S-61 | Add ingredient | Click Add → Fill mat_sap_code, re_code, name, unit, group → Save | Ingredient created | ⬜ | | | |
| S-62 | Edit ingredient | Click Edit → Modify fields → Save | Ingredient updated | ⬜ | | | |
| S-63 | Delete ingredient | Click Delete → Confirm | Ingredient removed | ⬜ | | | |
| S-64 | Print label | Click Print → Preview label | QR label generated and printed | ⬜ | | | |
| S-65 | Filter ingredients | Use column filter inputs | Table filtered by column values | ⬜ | | | |
| S-66 | Package container type | Manage container types (Bag, Drum, etc.) | Container types CRUD works | ⬜ | | | |
| S-67 | Standard package size | Set `std_package_size` on ingredient | Value saved and used in PreBatch | ⬜ | | | |

### 1.7 Warehouse Configuration (`x12-WarehouseConfig.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-70 | Warehouse list loads | Navigate to `/x12-WarehouseConfig` | Table with warehouses | ⬜ | | | |
| S-71 | Add warehouse | Click Add → Fill ID, Name, Description → Save | Warehouse added | ⬜ | | | |
| S-72 | Edit warehouse | Click Edit → Modify → Save | Warehouse updated | ⬜ | | | |
| S-73 | Delete warehouse | Click Delete → Confirm | Warehouse removed | ⬜ | | | |

### 1.8 Production Plan (`x30-ProductionPlan.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-80 | Plan list loads | Navigate to `/x30-ProductionPlan` | Table with production plans | ⬜ | | | |
| S-81 | Create plan | Select SKU → Set volume → Set plant → Save | Plan created with auto-generated batches | ⬜ | | | |
| S-82 | Auto batch calculation | Enter total volume + batch standard | Number of batches calculated automatically | ⬜ | | | |
| S-83 | Manual batch count | Override batch count manually | Batch count updated | ⬜ | | | |
| S-84 | Cancel plan | Click Cancel → Select reason → Confirm | Plan status → Cancelled, reason recorded | ⬜ | | | |
| S-85 | View plan history | Click History icon | Audit trail dialog shows changes | ⬜ | | | |
| S-86 | Print batch label | Click print on batch row | Batch label printed with QR code | ⬜ | | | |
| S-87 | Print all batch labels | Click "Print All" on plan | All batch labels printed sequentially | ⬜ | | | |
| S-88 | Print plan summary | Click Print Plan | Plan summary printed | ⬜ | | | |
| S-89 | Expand/collapse batches | Click expand row / Expand All | Batch details shown/hidden | ⬜ | | | |
| S-90 | Filter cancelled plans | Toggle "Show All" | Cancelled plans shown/hidden | ⬜ | | | |
| S-91 | Plant selection | Select FH / SPP plant | Batch standard auto-fills | ⬜ | | | |

### 1.9 System Dashboard (`x90-systemDashboard.vue`) — Admin Only

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-100 | Dashboard loads | Navigate to `/x90-systemDashboard` | Server status cards and charts display | ⬜ | | | |
| S-101 | CPU monitoring | View CPU chart | Real-time CPU usage displayed | ⬜ | | | |
| S-102 | Memory monitoring | View Memory card | RAM usage (used/total/percent) | ⬜ | | | |
| S-103 | Disk monitoring | View Disk card | Storage usage displayed | ⬜ | | | |
| S-104 | Auto-refresh | Wait 3 seconds | Metrics auto-refresh | ⬜ | | | |
| S-105 | PC Info display | View PC Info card | Hostname, OS, Platform, CPU model shown | ⬜ | | | |
| S-106 | System uptime | View Uptime card | Server uptime displayed | ⬜ | | | |
| S-107 | Manual refresh | Click "Refresh Metrics" | Metrics update immediately | ⬜ | | | |

### 1.10 Ingredient Intake Report (`x13-IngredientIntakeReport.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-110 | Report page loads | Navigate to `/x13-IngredientIntakeReport` | Date filter form and empty table | ⬜ | | | |
| S-111 | Generate report | Set start/end date → Click Generate | Report table populated with summary data | ⬜ | | | |
| S-112 | Grand totals | Generate report with data | Bottom row shows grand total volume and packages | ⬜ | | | |
| S-113 | Date validation | Click Generate with empty dates | Warning notification | ⬜ | | | |
| S-114 | Date picker | Click calendar icon | Date picker popup appears, date gets filled | ⬜ | | | |

### 1.11 About & Translation Editor (`x99-About.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| S-120 | About page loads | Navigate to `/x99-About` | About page with features and tech stack | ⬜ | | | |
| S-121 | Translation Editor open | Click "Translation Editor" button | Full-screen translation editor opens | ⬜ | | | |
| S-122 | Search translation | Type in search field | Filters translation rows by key/value | ⬜ | | | |
| S-123 | Edit translation | Click edit icon → Modify EN/TH → Save | Translation updated, UI refreshes | ⬜ | | | |
| S-124 | Add new translation | Click Add → Enter key, EN, TH → Save | New translation key created | ⬜ | | | |
| S-125 | Section filter | Select section from dropdown | Only shows keys from that section | ⬜ | | | |

---

## 2️⃣ Intake & PreBatch Station — FH (Flavour House)

> **Location:** FH Warehouse  
> **Equipment:** PC, Barcode Scanner, Barcode Printer, Weight Scale ×3  
> **Purpose:** Receive ingredients, weigh & prepare batches for FH warehouse

### 2.1 Ingredient Intake (`x10-IngredientIntake.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| FH-01 | Page loads | Navigate to `/x10-IngredientIntake` | Intake form + receipt history table | ⬜ | | | |
| FH-02 | MQTT connection | Check MQTT indicator | Shows connected to local device bridge | ⬜ | | | |
| FH-03 | Scan ingredient barcode | Scan barcode with scanner | `ingredientId` field auto-fills, ingredient info auto-looks up | ⬜ | | | |
| FH-04 | Manual ingredient lookup | Type ingredient ID → Enter | Ingredient details (name, re_code, unit) populate | ⬜ | | | |
| FH-05 | Blind code lookup | Scan/type blind code | Resolves to actual ingredient | ⬜ | | | |
| FH-06 | Generate Intake Lot ID | Click "Generate" or auto-trigger | New unique Intake Lot ID generated | ⬜ | | | |
| FH-07 | Set Intake From | Select intake source from dropdown | Source recorded (e.g., Supplier name) | ⬜ | | | |
| FH-08 | Add new Intake From | Click Add → Enter new source name → Save | New Intake From option available | ⬜ | | | |
| FH-09 | Set Intake To (Warehouse) | Select destination warehouse | Warehouse recorded | ⬜ | | | |
| FH-10 | Add new Warehouse option | Click Add → Enter warehouse → Save | New warehouse option added | ⬜ | | | |
| FH-11 | Volume entry | Enter intake volume (kg) | Volume validates as number | ⬜ | | | |
| FH-12 | Package calculation | Enter volume + package size | Number of packages auto-calculated | ⬜ | | | |
| FH-13 | Save receipt (Create) | Fill all fields → Save | Receipt saved to database, success notification | ⬜ | | | |
| FH-14 | Print intake label | Save triggers label print | Barcode label printed on Barcode Printer | ⬜ | | | |
| FH-15 | Test 1-page print | Click "Test Print 1 Page" | Single-page test label prints | ⬜ | | | |
| FH-16 | Test 2-page print | Click "Test Print 2 Pages" | Two-page test label prints | ⬜ | | | |
| FH-17 | Edit existing receipt | Click Edit on a receipt row | Form populates with existing data, Edit mode active | ⬜ | | | |
| FH-18 | Update receipt (Save) | Modify fields → Save | Receipt updated, notification shown | ⬜ | | | |
| FH-19 | View receipt details | Click row → Detail dialog | Detail dialog shows all fields + history | ⬜ | | | |
| FH-20 | Receipt history table | Scroll table | Shows intake_lot_id, re_code, material_desc, volume, dates, status | ⬜ | | | |
| FH-21 | Show all receipts | Toggle "Show All" | Includes completed/cancelled receipts | ⬜ | | | |
| FH-22 | Export data | Click Export | Data exported to CSV/file | ⬜ | | | |
| FH-23 | Scanner refocus | After save, scanner focus | Scanner input field automatically refocused | ⬜ | | | |

### 2.2 PreBatch Preparation (`x40-PreBatch.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| FH-30 | Page loads | Navigate to `/x40-PreBatch` | PreBatch page with production plan selector | ⬜ | | | |
| FH-31 | Select production plan | Choose plan from dropdown | Plan details load, batches shown | ⬜ | | | |
| FH-32 | Select batch | Click on a batch | Batch ingredients listed in recheck list | ⬜ | | | |
| FH-33 | View ingredient requirements | Select batch | Shows re_code, required volume, tolerance per ingredient | ⬜ | | | |
| FH-34 | Select ingredient (re_code) | Click ingredient in list | Ingredient selected, inventory filtered | ⬜ | | | |
| FH-35 | Select warehouse (FH) | Choose FH warehouse | Shows only FH inventory items | ⬜ | | | |
| FH-36 | View inventory | Check inventory panel | Shows available lots with quantities | ⬜ | | | |
| FH-37 | Select inventory item | Click inventory item | Weight scale targets set | ⬜ | | | |
| FH-38 | Scale connection | Check scale indicator | Weight Scale shows connected (MQTT) | ⬜ | | | |
| FH-39 | Toggle scale connection | Click connect/disconnect | Scale connects/disconnects | ⬜ | | | |
| FH-40 | Read weight (Scale 1) | Place ingredient on Scale 1 | Live weight reading displayed | ⬜ | | | |
| FH-41 | Read weight (Scale 2) | Place ingredient on Scale 2 | Live weight reading displayed | ⬜ | | | |
| FH-42 | Read weight (Scale 3) | Place ingredient on Scale 3 | Live weight reading displayed | ⬜ | | | |
| FH-43 | Tare scale | Click Tare button | Scale reading zeros | ⬜ | | | |
| FH-44 | Weight tolerance check | Weigh ingredient | Background color changes (green=OK, red=over, yellow=under) | ⬜ | | | |
| FH-45 | Tolerance exceeded alert | Exceed tolerance range | Warning indicator / alert shown | ⬜ | | | |
| FH-46 | Add lot to batch | Click Add Lot | Lot source recorded for traceability | ⬜ | | | |
| FH-47 | Remove lot | Click Remove Lot | Lot removed from batch record | ⬜ | | | |
| FH-48 | Update require volume | Admin modifies required volume | Volume updated in plan | ⬜ | | | |
| FH-49 | Container size selection | Select container size | Package size applied to calculation | ⬜ | | | |
| FH-50 | Package size lock | Toggle lock on package size | Size locked/unlocked for editing | ⬜ | | | |
| FH-51 | Request batch from inventory | Click Request | Inventory reserved for batch | ⬜ | | | |
| FH-52 | Prebatch record log | View prebatch log table | Shows each package: weight, status, timestamp | ⬜ | | | |
| FH-53 | Delete prebatch record | Click Delete → Enter password → Confirm | Record deleted, requires auth | ⬜ | | | |
| FH-54 | Finalize batch preparation | Click Finalize/Done | Batch status updated, items locked | ⬜ | | | |
| FH-55 | Print prebatch label | Click Print Label | Label with QR, batch ID, ingredient, weight printed | ⬜ | | | |
| FH-56 | Reprint label | Click Reprint on existing record | Label reprinted | ⬜ | | | |
| FH-57 | Quick reprint | Use quick reprint function | Last label reprinted quickly | ⬜ | | | |
| FH-58 | Print all plan labels | Click "Print All Plan" | All labels for plan printed | ⬜ | | | |
| FH-59 | Print all batch labels | Click "Print All Batch" | All labels for batch printed | ⬜ | | | |
| FH-60 | Print packing box label | Click Print Packing Box | Packing box label printed | ⬜ | | | |
| FH-61 | Scan intake lot barcode | Scan intake lot label | Intake lot auto-fills for source tracking | ⬜ | | | |
| FH-62 | Packaged volume indicator | Weigh multiple packages | Running total vs required shown with color coding | ⬜ | | | |

### 2.3 Packing List — FH View (`x50-PackingList.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| FH-70 | Page loads | Navigate to `/x50-PackingList` | 3-panel layout: Plans, Warehouse Bags, Batch Packing | ⬜ | | | |
| FH-71 | View active plans | Check left panel | Active production plans listed | ⬜ | | | |
| FH-72 | Select plan | Click a plan | Plan batches expand in middle panel | ⬜ | | | |
| FH-73 | Select batch | Click a batch | FH bags shown in middle panel | ⬜ | | | |
| FH-74 | FH bags display | View FH column | Shows bags grouped by re_code with tree view | ⬜ | | | |
| FH-75 | Bag sort toggle | Click column header | Bags sort by re_code/weight/status/batch_id | ⬜ | | | |
| FH-76 | Scan batch barcode | Scan batch QR code | Batch selected, details loaded | ⬜ | | | |
| FH-77 | Scan FH bag | Scan bag barcode at FH | Bag marked as packed, correct sound plays | ⬜ | | | |
| FH-78 | Wrong bag scan | Scan bag from wrong batch | Wrong bag alert, error sound plays | ⬜ | | | |
| FH-79 | All FH packed check | Pack all FH bags | "All FH Packed" indicator turns green | ⬜ | | | |
| FH-80 | Sound settings | Click Sound icon → Adjust | Volume, correct/wrong sounds configurable | ⬜ | | | |
| FH-81 | Sound persistence | Change sound settings → Refresh | Settings retained from localStorage | ⬜ | | | |

---

## 3️⃣ Intake & PreBatch Station — SPP

> **Location:** SPP Warehouse  
> **Equipment:** PC, Barcode Scanner, Barcode Printer, Weight Scale ×3  
> **Purpose:** Receive ingredients, weigh & prepare batches for SPP warehouse

### 3.1 Ingredient Intake (`x10-IngredientIntake.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| SPP-01 | Page loads | Navigate to `/x10-IngredientIntake` | Intake form + receipt history table | ⬜ | | | |
| SPP-02 | MQTT connection | Check MQTT indicator | Shows connected to SPP station device bridge | ⬜ | | | |
| SPP-03 | Scan barcode (SPP scanner) | Scan ingredient label | Ingredient identified, auto-lookup works | ⬜ | | | |
| SPP-04 | Save receipt (SPP) | Fill fields → Save | Receipt saved with SPP warehouse destination | ⬜ | | | |
| SPP-05 | Print label (SPP printer) | Save triggers print | Label prints on SPP Barcode Printer | ⬜ | | | |
| SPP-06 | Scanner refocus | After action | Input refocuses to scanner field | ⬜ | | | |

### 3.2 PreBatch Preparation (`x40-PreBatch.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| SPP-10 | Select SPP warehouse | Choose SPP warehouse filter | Only SPP inventory items displayed | ⬜ | | | |
| SPP-11 | Scale 1 (SPP) | Place on Scale 1 | Live weight reading from SPP scale | ⬜ | | | |
| SPP-12 | Scale 2 (SPP) | Place on Scale 2 | Live weight reading from SPP scale | ⬜ | | | |
| SPP-13 | Scale 3 (SPP) | Place on Scale 3 | Live weight reading from SPP scale | ⬜ | | | |
| SPP-14 | Weigh & record (SPP) | Weigh ingredient → Confirm | PreBatch record saved for SPP | ⬜ | | | |
| SPP-15 | Print label (SPP) | After weighing | PreBatch label prints on SPP Barcode Printer | ⬜ | | | |
| SPP-16 | Tolerance validation | Weigh outside tolerance | Visual and audio warning | ⬜ | | | |

### 3.3 Packing List — SPP View (`x50-PackingList.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| SPP-20 | SPP bags display | Select batch → View SPP column | SPP bags shown grouped by re_code | ⬜ | | | |
| SPP-21 | Scan SPP bag | Scan bag barcode at SPP | Bag marked as packed, correct sound | ⬜ | | | |
| SPP-22 | Wrong bag (SPP) | Scan wrong batch bag | Error alert + wrong sound | ⬜ | | | |
| SPP-23 | All SPP packed | Pack all SPP bags | "All SPP Packed" indicator green | ⬜ | | | |

---

## 4️⃣ Batch Recheck Station

> **Location:** QC / Recheck Area  
> **Equipment:** PC, Barcode Scanner  
> **Purpose:** Verify that each packing box contains the correct bags before release to production

### 4.1 Batch Recheck (`x60-BatchRecheck.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| RC-01 | Page loads | Navigate to `/x60-BatchRecheck` | Recheck page with box scan bar | ⬜ | | | |
| RC-02 | Scan packing box | Scan box barcode | Box details loaded: batch ID, list of bags | ⬜ | | | |
| RC-03 | Box details display | After box scan | Shows total bags, scanned count, progress bar | ⬜ | | | |
| RC-04 | Scan correct bag | Scan bag that belongs to box | Bag status → verified (✅), success sound + green feedback | ⬜ | | | |
| RC-05 | Scan duplicate bag | Re-scan already verified bag | Warning feedback shown | ⬜ | | | |
| RC-06 | Scan wrong bag (same batch) | Scan bag not in this box | Error feedback, bag not verified | ⬜ | | | |
| RC-07 | Scan wrong box bag | Scan bag from different batch | **Full-screen WRONG BOX alert** + loud alarm sound | ⬜ | | | |
| RC-08 | Progress tracking | Scan bags one by one | Progress bar fills, scanned/total count updates | ⬜ | | | |
| RC-09 | All verified | Scan all correct bags | `allVerified` = true, Release button enabled | ⬜ | | | |
| RC-10 | Release batch | Click Release | Batch status → Released, API called | ⬜ | | | |
| RC-11 | Reset box | Click Reset | Clears current box, ready for next scan | ⬜ | | | |
| RC-12 | Sound settings | Click Sound icon → Configure | Choose sound preset (chime/buzzer/siren/horn/alarm) | ⬜ | | | |
| RC-13 | Sound test | Change preset → Trigger scan | Correct preset sound plays | ⬜ | | | |
| RC-14 | Scanner simulator (box) | Click Simulator → Select batch → Click box label | Simulates box barcode scan | ⬜ | | | |
| RC-15 | Scanner simulator (bags) | Click bag labels in simulator | Simulates bag scans one by one | ⬜ | | | |
| RC-16 | Simulator wrong bag | Click "wrong bag" label | Simulates wrong-box scenario with full alert | ⬜ | | | |
| RC-17 | Error count | Scan wrong bags | Error count increments correctly | ⬜ | | | |
| RC-18 | Status icons | View bag list | Correct icons (✅ verified, ⬜ pending, ❌ error) | ⬜ | | | |

---

## 5️⃣ Mixing Production Stations (Mix_1, Mix_2, Mix_3)

> **Location:** Mixing Production Floor  
> **Equipment:** Barcode Scanner → IOT2050 → PLC  
> **Purpose:** Scan & verify bags at mixing point, send confirmed data to PLC

### 5.1 Packing List — Mixing Verification (`x50-PackingList.vue`)

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| MX-01 | Scan batch at Mix_1 | Scan batch QR at Mix_1 scanner | Batch loaded on Packing List page | ⬜ | | | |
| MX-02 | Scan batch at Mix_2 | Scan batch QR at Mix_2 scanner | Batch loaded on Packing List page | ⬜ | | | |
| MX-03 | Scan batch at Mix_3 | Scan batch QR at Mix_3 scanner | Batch loaded on Packing List page | ⬜ | | | |
| MX-04 | IOT2050 communication | Scan at Mixing station | IOT2050 receives scan data via MQTT | ⬜ | | | |
| MX-05 | PLC handshake | IOT2050 processes scan | PLC receives confirmed bag data | ⬜ | | | |
| MX-06 | Bag verification at mixer | Scan each bag before adding to mixer | Each bag verified against batch packing list | ⬜ | | | |
| MX-07 | Wrong bag at mixer | Scan wrong batch bag | Alert triggered, mixer does not proceed | ⬜ | | | |
| MX-08 | All bags scanned | Scan all bags for batch | Batch marked as complete at mixing station | ⬜ | | | |

---

## 6️⃣ Cross-Station / Integration Tests

> **Purpose:** Validate end-to-end workflow across all stations

| # | Test Case | Stations | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|---|
| INT-01 | Full workflow: Intake → PreBatch → Packing → Recheck | FH/SPP → Recheck | 1. Intake ingredient 2. Create plan 3. PreBatch weigh 4. Pack bags 5. Recheck box | Data flows correctly through all stages | ⬜ | | | |
| INT-02 | FH + SPP same batch | FH + SPP | Create plan with FH & SPP ingredients → PreBatch at both stations | Both warehouses show correct bags | ⬜ | | | |
| INT-03 | Inventory deduction | FH/SPP | Intake 100kg → Use 25kg in PreBatch | Remaining stock = 75kg | ⬜ | | | |
| INT-04 | Label traceability | All | Scan batch label → Verify all prebatch labels inside | All labels traceable to intake lots | ⬜ | | | |
| INT-05 | Multi-language across stations | All | Switch to Thai on FH, English on SPP | Each station shows correct language independently | ⬜ | | | |
| INT-06 | Permission enforcement | All | Login as Operator → Try admin features | Admin features inaccessible, correct redirects | ⬜ | | | |
| INT-07 | Concurrent users | FH + SPP | Both stations working on same plan | No data conflicts, correct isolation | ⬜ | | | |
| INT-08 | Network interruption | All | Disconnect network briefly → Reconnect | Data resumes syncing, no loss | ⬜ | | | |
| INT-09 | MQTT reconnection | FH/SPP | Stop MQTT broker → Restart | Scale/scanner readings resume automatically | ⬜ | | | |
| INT-10 | Print queue | FH/SPP | Print multiple labels rapidly | All labels print in order without jam | ⬜ | | | |

---

## 7️⃣ Navigation & UI Tests

| # | Test Case | Steps | Expected Result | Status | Tester | Date | Remark |
|---|---|---|---|---|---|---|---|
| UI-01 | Tab navigation | Click each nav tab | Correct page loads for each tab | ⬜ | | | |
| UI-02 | Permission-based tabs | Login with different roles | Tabs shown/hidden based on permissions | ⬜ | | | |
| UI-03 | Zoom control | Adjust zoom slider (80%→250%) | Page zooms correctly, layout intact | ⬜ | | | |
| UI-04 | Zoom persistence | Set zoom → Refresh page | Zoom level retained from localStorage | ⬜ | | | |
| UI-05 | Language toggle (EN/TH) | Click flag icon | All labels switch language | ⬜ | | | |
| UI-06 | Responsive layout | Resize browser window | Layout adapts without breaking | ⬜ | | | |
| UI-07 | Login/logout button | Check header | Shows Login when not auth'd, Logout when auth'd | ⬜ | | | |
| UI-08 | Logout flow | Click Logout | Session cleared, redirect to home, notification shown | ⬜ | | | |

---

## 📊 Test Summary

| Station | Total Tests | ✅ Passed | ❌ Failed | ⚠️ Issues | ⬜ Pending |
|---|---|---|---|---|---|
| Server Station | 48 | | | | 48 |
| FH Station | 35 | | | | 35 |
| SPP Station | 13 | | | | 13 |
| Recheck Station | 18 | | | | 18 |
| Mixing (Mix_1/2/3) | 8 | | | | 8 |
| Integration Tests | 10 | | | | 10 |
| UI/Navigation Tests | 8 | | | | 8 |
| **TOTAL** | **140** | | | | **140** |

---

## ✍️ Sign-off

| Role | Name | Signature | Date |
|---|---|---|---|
| **Project Manager** | | | |
| **Developer Lead** | | | |
| **QA / Tester** | | | |
| **Customer Representative** | | | |
| **IT Infrastructure** | | | |

---

> [!NOTE]
> This document should be used alongside the live system. Each test case should be executed on the physical station with the actual equipment connected. Results should be updated in real-time during the handover session.

> [!IMPORTANT]
> All **❌ Failed** items must be documented with detailed remarks and resolved before final handover approval.
