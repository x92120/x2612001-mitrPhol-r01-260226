# SKU Master View - Function Testing Checklist

## 🎯 **Testing URL**
`http://localhost:3000/x20-Sku`

---

## ✅ **Action Bar Buttons - All Functions**

### **1. New SKU Button** (Green + icon)
- [ ] Click button opens SKU creation dialog
- [ ] Dialog has all required fields (SKU ID, Name, Description, Status)
- [ ] Can create a new SKU successfully
- [ ] Shows success notification
- [ ] Table refreshes with new SKU

### **2. Refresh Button** (Blue refresh icon)
- [ ] Click button triggers `refreshAll()` function
- [ ] Fetches SKU Masters
- [ ] Fetches Actions
- [ ] Fetches Destinations
- [ ] Fetches Phases
- [ ] Fetches Ingredients
- [ ] Shows loading state during refresh
- [ ] Table updates with latest data

### **3. Reset Filters Button** (Blue filter_alt_off icon)
- [ ] Click button clears search filter
- [ ] Resets "Show All" checkbox to false
- [ ] Shows "Filters reset" notification
- [ ] Table shows filtered results

### **4. Show/Hide Filters Button** (Pink filter_alt icon)
- [ ] Click button toggles `showFilters` state
- [ ] Tooltip changes between "Show Filters" and "Hide Filters"
- [ ] Filter inputs appear/disappear in table headers
- [ ] Icon color is accent (pink)

### **5. Export Excel Button** (Teal file_download icon)
- [ ] Click button triggers `exportToExcel()` function
- [ ] Uses selected SKUs or all SKUs
- [ ] Downloads Excel file with timestamp
- [ ] Shows "Export successful" notification
- [ ] File contains correct SKU data

### **6. Import CSV Button** (Pink file_upload icon)
- [ ] Click button triggers hidden file input
- [ ] File dialog opens accepting .csv files
- [ ] Can select a CSV file
- [ ] Uploads to `/skus/import` endpoint
- [ ] Shows success/error notification
- [ ] Refreshes SKU list after import
- [ ] File input clears after processing

### **7. Actions/Settings Button** (Pink settings icon)
- [ ] Click button opens Actions dialog
- [ ] Can view existing actions
- [ ] Can add new action (action_code, description)
- [ ] Can edit existing action
- [ ] Can delete action with confirmation
- [ ] Search filter works for actions
- [ ] Shows success notifications

---

## 🔍 **Search and Filter Features**

### **Search Box**
- [ ] Can type in search box
- [ ] Filters SKUs by SKU ID
- [ ] Filters SKUs by SKU Name
- [ ] Filters SKUs by Description
- [ ] Clear button (X) clears search
- [ ] Search is case-insensitive
- [ ] Results update in real-time

### **Show All Checkbox**
- [ ] Checkbox toggles `showAllIncludingInactive`
- [ ] When checked: shows inactive SKUs
- [ ] When unchecked: hides inactive SKUs
- [ ] Works with search filter

### **Column Filters** (when Show Filters is active)
- [ ] Filter inputs appear in table headers
- [ ] Can filter by SKU ID
- [ ] Can filter by SKU Name
- [ ] Can filter by Description
- [ ] Can filter by Status
- [ ] Multiple filters work together
- [ ] Filters are case-insensitive

---

## 📊 **SKU Table Functions**

### **Table Display**
- [ ] Shows all SKU columns correctly
- [ ] Status column shows colored chips
- [ ] Active = Green chip
- [ ] Inactive = Grey chip
- [ ] Pagination works if many SKUs
- [ ] Rows are clickable/expandable

### **Expand SKU Row**
- [ ] Click row expands to show process steps
- [ ] Steps are grouped by phase
- [ ] Phase headers show phase number and description
- [ ] Can expand/collapse individual phases
- [ ] Steps show all details (action, ingredient, quantity, etc.)

---

## 🔧 **SKU Step Management**

### **Add New Phase**
- [ ] "Add Phase" button visible in expanded view
- [ ] Click opens step dialog with new phase number
- [ ] Phase number auto-increments (p0010, p0020, etc.)
- [ ] Can select phase from dropdown
- [ ] `master_step` is set to true for first step in phase
- [ ] Step saves successfully
- [ ] Phase appears in expanded view

### **Add Step to Existing Phase**
- [ ] "+ Step" button visible for each phase
- [ ] Click opens step dialog
- [ ] Pre-fills phase number and phase_id
- [ ] Sub-step auto-increments (10, 20, 30, etc.)
- [ ] `master_step` is false for additional steps
- [ ] Step saves successfully
- [ ] Step appears in correct phase

### **Edit Step**
- [ ] Click edit icon on step row
- [ ] Opens step dialog with current values
- [ ] Can modify all fields
- [ ] Save updates the step
- [ ] `sku_id` cannot be changed (backend validation)
- [ ] Shows success notification

### **Copy Step**
- [ ] Click copy icon on step row
- [ ] Opens step dialog with copied values
- [ ] Step ID is cleared (new step)
- [ ] Can modify before saving
- [ ] Saves as new step
- [ ] Shows success notification

### **Delete Step**
- [ ] Click delete icon on step row
- [ ] Shows confirmation dialog
- [ ] Can confirm or cancel
- [ ] Deletes step on confirm
- [ ] Shows success notification
- [ ] Step removed from view

### **Delete Entire Phase**
- [ ] Delete icon visible in phase header
- [ ] Click shows confirmation with step count
- [ ] Confirms deletion of all steps in phase
- [ ] Deletes all steps successfully
- [ ] Shows success notification with count
- [ ] Phase removed from view

---

## 📝 **Step Dialog Functions**

### **Step Form Fields**
- [ ] Phase Number (dropdown)
- [ ] Phase ID (auto-filled from phase)
- [ ] Sub Step (number)
- [ ] Action (dropdown with search)
- [ ] RE Code / Ingredient (dropdown with search, filtered by action)
- [ ] Action Code (auto-filled from action)
- [ ] Action Description (auto-filled from action)
- [ ] Destination (dropdown)
- [ ] Require (number)
- [ ] UOM (text)
- [ ] Low Tolerance (number)
- [ ] High Tolerance (number)
- [ ] Step Condition (text)
- [ ] Agitator RPM (number)
- [ ] High Shear RPM (number)
- [ ] Temperature (number)
- [ ] Temp Low (number)
- [ ] Temp High (number)
- [ ] Step Time (number)
- [ ] Brix SP (text)
- [ ] pH SP (text)
- [ ] QC Temp (checkbox)
- [ ] Record Steam Pressure (checkbox)
- [ ] Record CTW (checkbox)
- [ ] Operation Brix Record (checkbox)
- [ ] Operation pH Record (checkbox)
- [ ] Master Step (checkbox, auto-set)

### **Step Form Validation**
- [ ] All required fields validated
- [ ] Numbers accept only numeric input
- [ ] Dropdowns show filtered options
- [ ] Ingredient filter works based on action
- [ ] Save button disabled until valid
- [ ] Cancel button closes dialog

### **Step Form Save**
- [ ] Creates new step if no step_id
- [ ] Updates existing step if step_id present
- [ ] `sku_id` is correctly set and preserved
- [ ] Shows success notification
- [ ] Closes dialog on success
- [ ] Refreshes step list

---

## 🎨 **Phase Management Dialog**

### **Phase Dialog**
- [ ] Opens from Actions menu
- [ ] Shows list of all phases
- [ ] Can search/filter phases
- [ ] Can add new phase
- [ ] Can edit existing phase
- [ ] Can delete phase (if not in use)
- [ ] Shows phase ID, code, and description

---

## 🔄 **Data Integrity**

### **SKU Step Scoping** (Critical Bug Fix)
- [ ] Adding step to SKU A doesn't affect SKU B
- [ ] `sku_id` is correctly set in `addStep()`
- [ ] `sku_id` is correctly set in `addStepToPhase()`
- [ ] Backend prevents `sku_id` changes on update
- [ ] Each SKU has independent step list
- [ ] `master_step` only affects current SKU

---

## 🚨 **Error Handling**

### **Network Errors**
- [ ] Shows error notification if API fails
- [ ] Handles 404 errors gracefully
- [ ] Handles 500 errors gracefully
- [ ] Handles timeout errors
- [ ] Loading states clear on error

### **Validation Errors**
- [ ] Shows validation errors in dialog
- [ ] Prevents invalid data submission
- [ ] Shows clear error messages
- [ ] Allows user to correct and retry

---

## 📱 **UI/UX Checks**

### **Visual Design**
- [ ] All icon buttons are round and flat
- [ ] Tooltips appear on hover
- [ ] Colors are consistent (green/blue/pink/teal)
- [ ] Icons are clear and recognizable
- [ ] Layout is clean and organized
- [ ] No overlapping elements

### **Responsiveness**
- [ ] Works on desktop
- [ ] Works on tablet
- [ ] Works on mobile
- [ ] Buttons don't overflow
- [ ] Tables scroll horizontally if needed

### **Performance**
- [ ] Page loads quickly
- [ ] No console errors
- [ ] No memory leaks
- [ ] Smooth animations
- [ ] Fast search/filter response

---

## 🎯 **Critical Functions Summary**

✅ **Must Work:**
1. ✓ Refresh - Loads all data
2. ✓ Add SKU - Creates new SKU
3. ✓ Add Step - Creates step with correct sku_id
4. ✓ Edit Step - Updates without changing sku_id
5. ✓ Delete Step - Removes step
6. ✓ Delete Phase - Removes all steps in phase
7. ✓ Search - Filters SKUs
8. ✓ Export - Downloads Excel
9. ✓ Import - Uploads CSV
10. ✓ Filters - Show/Hide/Reset

---

## 📋 **Test Execution Notes**

**Date:** _____________
**Tester:** _____________
**Browser:** _____________
**Version:** _____________

**Overall Status:** ⬜ Pass ⬜ Fail ⬜ Partial

**Issues Found:**
_____________________________________________
_____________________________________________
_____________________________________________

**Notes:**
_____________________________________________
_____________________________________________
_____________________________________________
