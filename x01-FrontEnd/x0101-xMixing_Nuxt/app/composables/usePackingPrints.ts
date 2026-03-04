/**
 * usePackingPrints — All label/report print functions for the Packing List page
 * Extracted from x50-PackingList.vue to keep the page component focused on UI logic.
 */
import QRCode from 'qrcode'
import { useLabelPrinter } from './useLabelPrinter'

export interface PackingPrintDeps {
    $q: any
    plans: any              // ref<any[]>
    selectedBatch: any      // ref
    batchInfo: any          // ref
    bagsByWarehouse: any    // ref<{ FH: any[], SPP: any[] }>
    allRecords: any         // ref<any[]>
    transferredBoxes: any   // ref<TransferredBox[]>
    selectedForTransfer: any // ref<string[]>
    showTransferDialog: any // ref<boolean>
}

export const usePackingPrints = (deps: PackingPrintDeps) => {
    const { generateLabelSvg, printLabel } = useLabelPrinter()

    // ── Helper: open A4 print window ──
    const openA4PrintWindow = (title: string, svgContent: string) => {
        const pw = Math.round(window.screen.width * 0.8)
        const ph = Math.round(window.screen.height * 0.8)
        const left = Math.round((window.screen.width - pw) / 2)
        const top = Math.round((window.screen.height - ph) / 2)
        const win = window.open('', '_blank', `width=${pw},height=${ph},left=${left},top=${top}`)
        if (!win) {
            deps.$q.notify({ type: 'warning', message: 'Popup blocked — allow popups and retry', position: 'top' })
            return null
        }
        win.document.write(`<!DOCTYPE html><html><head>
      <title>${title}</title>
      <style>
        * { margin:0; padding:0; box-sizing:border-box; }
        body { background:#888; display:flex; justify-content:center; align-items:flex-start; padding:20px; }
        .page { background:#fff; box-shadow:0 4px 20px rgba(0,0,0,.4); }
        @media print {
          body { background:white; padding:0; }
          .page { box-shadow:none; }
          @page { size: A4 portrait; margin:0; }
        }
      </style>
    </head><body>
      <div class="page">${svgContent}</div>
      <script>window.onload = () => { setTimeout(() => window.print(), 400) }<\/script>
    </body></html>`)
        win.document.close()
        return win
    }

    // ── Helper: open 4x3 print window ──
    const open4x3PrintWindow = (title: string, svgContent: string) => {
        const pw = Math.round(window.screen.width * 0.8)
        const ph = Math.round(window.screen.height * 0.8)
        const left = Math.round((window.screen.width - pw) / 2)
        const top = Math.round((window.screen.height - ph) / 2)
        const win = window.open('', '_blank', `width=${pw},height=${ph},left=${left},top=${top}`)
        if (!win) {
            deps.$q.notify({ type: 'warning', message: 'Popup blocked — allow popups and retry', position: 'top' })
            return null
        }
        win.document.write(`<!DOCTYPE html><html><head>
      <title>${title}</title>
      <style>
        @page { size: 4in 3in; margin: 0; }
        body  { margin: 0; padding: 0; background: #fff; }
        svg   { display: block; width: 4in; height: 3in; }
      </style>
    </head><body>
      ${svgContent}
      <script>window.onload = () => { window.print(); window.onafterprint = () => window.close(); }<\/script>
    </body></html>`)
        win.document.close()
        return win
    }

    // ── Helper: generate report number ──
    const makeReportNo = (prefix: string) => {
        const now = new Date()
        return `${prefix}-${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}-${String(Math.floor(Math.random() * 9000) + 1000)}`
    }

    // ═══════════════════════════════════════════════════════════════════
    // 1. PACKING BOX DETAIL REPORT (A4)
    // ═══════════════════════════════════════════════════════════════════
    const printPackingBoxReport = async (batchId: string, wh: 'FH' | 'SPP') => {
        const plan = deps.plans.value.find((p: any) => p.batches?.some((b: any) => b.batch_id === batchId))
        const batch = plan?.batches?.find((b: any) => b.batch_id === batchId)
        const whBags = wh === 'FH' ? deps.bagsByWarehouse.value.FH : deps.bagsByWarehouse.value.SPP

        let bags = whBags.filter((b: any) => b.re_code)
        if (deps.selectedBatch.value?.batch_id !== batchId) {
            bags = deps.allRecords.value.filter((r: any) => {
                const matchBatch = r.plan_id === plan?.plan_id && r.batch_record_id?.startsWith(batchId)
                const matchWh = wh === 'FH'
                    ? ['FH', 'CL', 'FL'].some(p => (r.re_code || '').toUpperCase().startsWith(p))
                    : !['FH', 'CL', 'FL'].some(p => (r.re_code || '').toUpperCase().startsWith(p))
                return matchBatch && matchWh
            })
        }

        const now = new Date()
        const dateStr = now.toLocaleDateString('th-TH', { year: 'numeric', month: '2-digit', day: '2-digit' })
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        const reportNo = makeReportNo('PB')
        const totalWeight = bags.reduce((s: number, b: any) => s + (b.net_volume || 0), 0)
        const ingredients = new Set(bags.map((b: any) => b.re_code)).size
        const boxEntry = deps.transferredBoxes.value.find((tb: any) => tb.batch_id === batchId && tb.wh === wh)
        const boxClosedTime = boxEntry?.time || '-'

        const ROW_H = 20, START = 192
        let rowsSvg = ''
        bags.sort((a: any, b: any) => {
            const codeA = a.re_code || ''; const codeB = b.re_code || ''
            if (codeA !== codeB) return codeA.localeCompare(codeB)
            return (a.package_no || 0) - (b.package_no || 0)
        })
        bags.forEach((bag: any, i: number) => {
            const y = START + i * ROW_H
            if (y + ROW_H > 980) return
            const bg = i % 2 === 0 ? '#f8f8f8' : '#ffffff'
            const packed = bag.packing_status === 1
            const statusColor = packed ? '#1b5e20' : '#b71c1c'
            const statusText = packed ? '✓ Packed' : '○ Pending'
            rowsSvg += `
        <rect x="20" y="${y}" width="754" height="${ROW_H}" fill="${bg}"/>
        <text x="38"  y="${y + 14}" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">${i + 1}</text>
        <text x="56"  y="${y + 14}" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${bag.re_code || '-'}</text>
        <text x="150" y="${y + 14}" style="font-size:7px;font-family:Arial,sans-serif;fill:#333333">${bag.ingredient_name || bag.re_code || '-'}</text>
        <text x="380" y="${y + 14}" style="font-size:7px;font-family:'Courier New',monospace;fill:#000000">${bag.batch_record_id || '-'}</text>
        <text x="560" y="${y + 14}" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">${bag.package_no || 1}/${bag.total_packages || 1}</text>
        <text x="600" y="${y + 14}" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${(bag.net_volume || 0).toFixed(4)}</text>
        <text x="710" y="${y + 14}" style="font-size:7px;font-family:Arial,sans-serif;font-weight:bold;fill:${statusColor}">${statusText}</text>
        <line x1="20" y1="${y + ROW_H}" x2="774" y2="${y + ROW_H}" stroke="#e0e0e0" stroke-width="0.3"/>
      `
        })

        try {
            const resp = await fetch('/labels/report-packingbox-a4.svg')
            let svgText = await resp.text()
            svgText = svgText
                .replace('{{ReportNo}}', reportNo)
                .replace('{{PrintDate}}', `${dateStr} ${timeStr}`)
                .replace('{{BatchId}}', batchId)
                .replace('{{SkuName}}', batch?.sku_name || deps.batchInfo.value?.sku_name || '-')
                .replace('{{Warehouse}}', wh)
                .replace('{{Plant}}', plan?.plant || '-')
                .replace('{{BoxClosedTime}}', boxClosedTime)
                .replace('{{TotalBags}}', String(bags.length))
                .replace('{{TotalWeight}}', totalWeight.toFixed(3))
                .replace('{{TotalIngredients}}', String(ingredients))
                .replace('{{PackingBoxRows}}', rowsSvg)

            const qrData = `BoxReport:${batchId}|WH:${wh}|Date:${dateStr}`
            const qrDataUrl = await QRCode.toDataURL(qrData, { width: 150, margin: 1 })
            svgText = svgText.replace('{{BoxQRCode}}', `<image x="0" y="0" width="150" height="150" href="${qrDataUrl}" />`)

            openA4PrintWindow(`Packing Box Report — ${batchId} [${wh}]`, svgText)
        } catch (e) {
            console.error('Print error:', e)
            deps.$q.notify({ type: 'negative', message: 'Failed to load report template', position: 'top' })
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // 2. TRANSFER REPORT (A4)
    // ═══════════════════════════════════════════════════════════════════
    const printTransferReport = async () => {
        const boxes = deps.transferredBoxes.value.filter((b: any) => deps.selectedForTransfer.value.includes(b.id))
        if (boxes.length === 0) return

        const now = new Date()
        const dateStr = now.toLocaleDateString('th-TH', { year: 'numeric', month: '2-digit', day: '2-digit' })
        const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        const reportNo = makeReportNo('TR')
        const whs = [...new Set(boxes.map((b: any) => b.wh))].join(' / ')
        const totalBags = boxes.reduce((s: number, b: any) => s + b.bagsCount, 0)

        const ROW_H = 26, START = 158
        let rowsSvg = ''
        boxes.forEach((box: any, i: number) => {
            const y = START + i * ROW_H
            const bg = i % 2 === 0 ? '#f2f2f2' : '#ffffff'
            const plan = deps.plans.value.find((p: any) => p.batches?.some((b: any) => b.batch_id === box.batch_id))
            const sku = plan?.sku_name || plan?.sku_id || '-'
            rowsSvg += `
        <rect x="20" y="${y}" width="754" height="${ROW_H}" fill="${bg}"/>
        <line x1="20" y1="${y + ROW_H}" x2="774" y2="${y + ROW_H}" stroke="#cccccc" stroke-width="0.4"/>
        <text x="36"  y="${y + 16}" style="font-size:8px;font-family:Arial,sans-serif;fill:#555555">${i + 1}</text>
        <text x="60"  y="${y + 14}" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${box.batch_id}</text>
        <text x="60"  y="${y + 24}" style="font-size:7px;font-family:'Courier New',monospace;fill:#888888">${box.id.slice(0, 8)}</text>
        <text x="230" y="${y + 16}" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">${sku.length > 28 ? sku.slice(0, 28) + '…' : sku}</text>
        <rect x="424" y="${y + 5}" width="28" height="14" rx="3" fill="#333333"/>
        <text x="438" y="${y + 16}" text-anchor="middle" style="font-size:8px;font-family:Arial,sans-serif;font-weight:bold;fill:#ffffff">${box.wh}</text>
        <text x="478" y="${y + 16}" style="font-size:9px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${box.bagsCount}</text>
        <text x="520" y="${y + 16}" style="font-size:8px;font-family:Arial,sans-serif;fill:#000000">${box.time}</text>
        <rect x="652" y="${y + 5}" width="56" height="14" rx="3" fill="#222222"/>
        <text x="680" y="${y + 16}" text-anchor="middle" style="font-size:7.5px;font-family:Arial,sans-serif;font-weight:bold;fill:#ffffff">TRANSFERRED</text>
      `;
            [52, 222, 422, 460, 512, 650].forEach(x => {
                rowsSvg += `<line x1="${x}" y1="${y}" x2="${x}" y2="${y + ROW_H}" stroke="#cccccc" stroke-width="0.4"/>`
            })
        })

        try {
            const resp = await fetch('/labels/report-transfer-a4.svg')
            let svgText = await resp.text()
            svgText = svgText
                .replace('{{ReportNo}}', reportNo)
                .replace('{{PrintDate}}', `${dateStr} ${timeStr}`)
                .replace('{{Warehouse}}', whs || 'FH / SPP')
                .replace('{{TransferDate}}', dateStr)
                .replace('{{TotalBoxes}}', String(boxes.length))
                .replace('{{TotalBags}}', String(totalBags))
                .replace('{{TransferRows}}', rowsSvg)
                .replace('{{ReportQR}}', '')
            openA4PrintWindow(`Transfer Report ${reportNo}`, svgText)
        } catch (e) {
            deps.$q.notify({ type: 'negative', message: 'Failed to load report template', position: 'top' })
        }
        deps.showTransferDialog.value = false
        deps.selectedForTransfer.value = []
    }

    // ═══════════════════════════════════════════════════════════════════
    // 3. BOX PACKING LABEL (4×3 inch)
    // ═══════════════════════════════════════════════════════════════════
    const printBoxLabel = async (wh: 'FH' | 'SPP') => {
        if (!deps.selectedBatch.value || !deps.batchInfo.value) return

        const bags = wh === 'FH' ? deps.bagsByWarehouse.value.FH : deps.bagsByWarehouse.value.SPP
        const plan = deps.plans.value.find((p: any) => p.batches?.some((b: any) => b.batch_id === deps.selectedBatch.value.batch_id))

        type BagGroup = { re_code: string; req_vol: number; bags: any[] }
        const grouped: BagGroup[] = []
        const seenCodes = new Map<string, BagGroup>()
        for (const bag of bags) {
            const code = bag.re_code || '?'
            if (!seenCodes.has(code)) {
                const g: BagGroup = { re_code: code, req_vol: bag.total_request_volume ?? bag.total_volume ?? 0, bags: [] }
                seenCodes.set(code, g)
                grouped.push(g)
            }
            seenCodes.get(code)!.bags.push(bag)
        }
        grouped.forEach(g => g.bags.sort((a: any, b: any) => (a.package_no ?? 0) - (b.package_no ?? 0)))

        const HDR_H = 12, PKG_H = 10, START_Y = 144
        let curY = START_Y
        let rowsSvg = ''
        for (const grp of grouped) {
            if (curY + HDR_H > 253) break
            rowsSvg += `
        <rect x="8" y="${curY}" width="368" height="${HDR_H}" fill="#ffffff"/>
        <text x="14" y="${curY + 8}" style="font-size:7px;font-family:Arial,sans-serif;font-weight:bold;fill:#000000">${grp.re_code}</text>
        <text x="370" y="${curY + 8}" text-anchor="end" style="font-size:7px;font-family:Arial,sans-serif;fill:#000000">Req ${grp.req_vol.toFixed(3)} kg</text>
        <line x1="8" y1="${curY + HDR_H}" x2="376" y2="${curY + HDR_H}" stroke="#000000" stroke-width="0.3"/>
      `
            curY += HDR_H
            for (const bag of grp.bags) {
                if (curY + PKG_H > 253) break
                const pkgLabel = `  Pkg ${bag.package_no ?? 1}/${bag.total_packages ?? 1}`
                rowsSvg += `
          <rect x="8" y="${curY}" width="368" height="${PKG_H}" fill="#ffffff"/>
          <text x="24" y="${curY + 7}" style="font-size:6px;font-family:'Courier New',monospace;fill:#000000">${pkgLabel}</text>
          <text x="370" y="${curY + 7}" text-anchor="end" style="font-size:6px;font-family:Arial,sans-serif;fill:#000000">${(bag.net_volume ?? 0).toFixed(3)} kg</text>
        `
                rowsSvg += `<line x1="24" y1="${curY + PKG_H}" x2="376" y2="${curY + PKG_H}" stroke="#000000" stroke-width="0.15"/>`
                curY += PKG_H
            }
        }

        const totalWt = bags.reduce((s: number, b: any) => s + (b.net_volume || 0), 0)
        const now = new Date()
        const printDate = now.toLocaleDateString('th-TH') + ' ' + now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

        try {
            const resp = await fetch('/labels/label-box-packing_4x3.svg')
            let svgText = await resp.text()
            svgText = svgText
                .replaceAll('{{Warehouse}}', wh)
                .replaceAll('{{PrintDate}}', printDate)
                .replace('{{SkuId}}', deps.batchInfo.value?.sku_name || '-')
                .replace('{{BatchId}}', deps.selectedBatch.value.batch_id)
                .replace('{{Plant}}', plan?.plant || deps.selectedBatch.value.plant || 'Line-1')
                .replace('{{BatchSize}}', (deps.batchInfo.value?.batch_size || 0).toFixed(0))
                .replace('{{TotalNetWeight}}', totalWt.toFixed(3))
                .replace('{{PreBatchRows}}', rowsSvg)

            const qrData = `Batch_ID:${deps.selectedBatch.value.batch_id}\nWarehouse:${wh}`
            const qrDataUrl = await QRCode.toDataURL(qrData, { width: 150, margin: 1, color: { dark: '#000000', light: '#ffffff' } })
            svgText = svgText.replace('{{BoxQRCode}}', `<image x="0" y="0" width="150" height="150" href="${qrDataUrl}" />`)

            open4x3PrintWindow(`Box Packing Label — ${deps.selectedBatch.value.batch_id} [${wh}]`, svgText)
        } catch (e) {
            console.error('Print error:', e)
            deps.$q.notify({ type: 'negative', message: 'Failed to load label template', position: 'top' })
        }
    }

    // ═══════════════════════════════════════════════════════════════════
    // 4. PRE-BATCH BAG LABEL (4×3 inch)
    // ═══════════════════════════════════════════════════════════════════
    const printBagLabel = async (bag: any) => {
        if (!deps.selectedBatch.value || !deps.batchInfo.value) return
        const plan = deps.plans.value.find((p: any) => p.batches?.some((b: any) => b.batch_id === deps.selectedBatch.value.batch_id))
        const data: Record<string, string | number> = {
            'SKU / SKU_Name': deps.batchInfo.value?.sku_name || '-',
            PlanId: deps.batchInfo.value?.plan_id || '-',
            BatchId: deps.selectedBatch.value.batch_id || '-',
            'Batch_Number/No of Batch': `Batch ${deps.selectedBatch.value.batch_id?.split('-').pop() || '?'}`,
            IngredientID: bag.re_code || '-',
            Ingredient_ReCode: bag.re_code || '-',
            mat_sap_code: bag.mat_sap_code || '-',
            PlanStartDate: plan?.start_date ? new Date(plan.start_date).toLocaleDateString('en-GB') : '-',
            PlanFinishDate: plan?.finish_date ? new Date(plan.finish_date).toLocaleDateString('en-GB') : '-',
            PrepareDate: new Date().toLocaleDateString('en-GB'),
            PlantId: plan?.plant || deps.selectedBatch.value.plant || '-',
            PlantName: '-',
            Timestamp: new Date().toLocaleString('en-GB'),
            PackageSize: (bag.net_volume || 0).toFixed(4),
            BatchRequireSize: (bag.total_volume || bag.total_request_volume || 0).toFixed(4),
            PackageNo: `${bag.package_no || 1}/${bag.total_packages || 1}`,
            QRCode: `${deps.batchInfo.value?.plan_id || ''},${bag.batch_record_id},${bag.re_code},${bag.net_volume}`,
            Lot1: bag.origins?.[0] ? `${bag.origins[0].intake_lot_id} / ${(bag.origins[0].take_volume || 0).toFixed(4)} kg` : (bag.intake_lot_id ? `${bag.intake_lot_id} / ${Number(bag.net_volume).toFixed(4)} kg` : '-'),
            Lot2: bag.origins?.[1] ? `${bag.origins[1].intake_lot_id} / ${(bag.origins[1].take_volume || 0).toFixed(4)} kg` : '',
        }
        const svg = await generateLabelSvg('prebatch-label_4x3', data)
        if (svg) printLabel(svg)
    }

    return {
        printPackingBoxReport,
        printTransferReport,
        printBoxLabel,
        printBagLabel,
    }
}
