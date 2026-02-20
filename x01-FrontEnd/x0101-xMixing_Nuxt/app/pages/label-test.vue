<template>
  <q-page padding class="flex flex-center bg-grey-2">
    <q-card style="width: 500px; border-radius: 12px;" class="shadow-10">
      <q-card-section class="bg-primary text-white">
        <div class="text-h6">🏷️ Label Designer Concept</div>
        <div class="text-subtitle2">SVG-based Template System</div>
      </q-card-section>

      <q-card-section class="q-gutter-md">
        <!-- Template Selection -->
        <q-select 
          v-model="selectedTemplate" 
          :options="['prebatch-label', 'ingredient-label']" 
          label="Select Template" 
          outlined 
          dense 
        />

        <q-separator />

        <!-- Production Label Fields -->
        <div v-if="selectedTemplate === 'prebatch-label'" class="q-gutter-y-sm">
          <q-input v-model="labelData.RecipeName" label="Recipe Name" dense outlined />
          <q-input v-model="labelData.OrderCode" label="Order Code" dense outlined />
          <div class="row q-col-gutter-sm">
            <q-input v-model="labelData.BaseQuantity" class="col" label="Base Qty" dense outlined />
            <q-input v-model="labelData.ItemNumber" class="col" label="Item #" dense outlined />
          </div>
          <div class="row q-col-gutter-sm">
            <q-input v-model="labelData.Weight" class="col" label="Weight (Act/Max)" dense outlined />
            <q-input v-model="labelData.Packages" class="col" label="Packages (n/N)" dense outlined />
          </div>
        </div>

        <!-- Ingredient Label Fields -->
        <div v-else class="q-gutter-y-sm">
          <q-input v-model="labelData.BATCH_ID" label="Batch ID" dense outlined />
          <q-input v-model="labelData.INGREDIENT_NAME" label="Ingredient Name" dense outlined />
          <div class="row q-col-gutter-sm">
            <q-input v-model="labelData.TARGET_WEIGHT" class="col" label="Target (kg)" type="number" dense outlined />
            <q-input v-model="labelData.ACTUAL_WEIGHT" class="col" label="Actual (kg)" type="number" dense outlined />
          </div>
        </div>

        <q-separator q-my-md />

        <!-- Preview Area -->
        <div class="text-overline text-center">Live Preview</div>
        <div 
          v-if="renderedSvg" 
          class="preview-container bg-white q-pa-md shadow-2 flex flex-center"
          v-html="renderedSvg"
        ></div>
        <div v-else class="preview-placeholder flex flex-center text-grey-6 border-dashed">
          Enter data to see preview
        </div>
      </q-card-section>

      <q-card-actions align="right" class="bg-grey-1">
        <q-btn flat label="Refresh Preview" icon="refresh" color="secondary" @click="updatePreview" />
        <q-btn label="Print Label" icon="print" color="primary" @click="handlePrint" />
      </q-card-actions>
    </q-card>
  </q-page>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch } from 'vue'
import { useLabelPrinter } from '~/composables/useLabelPrinter'

const { generateLabelSvg, printLabel } = useLabelPrinter()

const selectedTemplate = ref('prebatch-label')

const labelData = reactive({
  // Common fields (Production Label)
  RecipeName: 'S77CA4SN02',
  BaseQuantity: '1000',
  ItemNumber: '10',
  RefCode: 'S710009900',
  OrderCode: 'ord251110-001',
  BatchSize: '500.00',
  Weight: '100.50/414.50',
  Packages: '1/5',
  
  // Legacy Ingredient fields
  BATCH_ID: 'B2025-001',
  INGREDIENT_NAME: 'Premium Flour Type A',
  TARGET_WEIGHT: 25.0,
  ACTUAL_WEIGHT: 25.04,
  OPERATOR: 'Admin Dev',
  PRINT_DATE: new Date().toLocaleDateString()
})

const renderedSvg = ref('')

const updatePreview = async () => {
  const svg = await generateLabelSvg(selectedTemplate.value, labelData)
  if (svg) {
    renderedSvg.value = svg
  }
}

const handlePrint = () => {
  if (renderedSvg.value) {
    printLabel(renderedSvg.value)
  }
}

// Update preview automatically when data changes
watch([labelData, selectedTemplate], () => updatePreview(), { deep: true })

onMounted(() => {
  updatePreview()
})
</script>

<style scoped>
.preview-container {
  border: 1px solid #ddd;
  min-height: 400px;
  background: #fff;
  overflow: hidden;
  display: flex;
  justify-content: center;
}

.preview-container :deep(svg) {
  height: 400px;
  width: auto;
  max-width: 100%;
}

.preview-placeholder {
  height: 250px;
  border: 2px dashed #ccc;
  border-radius: 8px;
}

.border-dashed {
  border: 2px dashed #ccc;
}
</style>
