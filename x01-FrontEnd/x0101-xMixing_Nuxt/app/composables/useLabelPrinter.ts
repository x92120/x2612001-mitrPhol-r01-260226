import QRCode from 'qrcode'

export const useLabelPrinter = () => {

  /**
   * Processes an SVG template by replacing placeholders with actual data
   * @param templateName Name of the svg file in /public/labels (e.g. 'ingredient-label')
   * @param data Object containing keys to replace {{KEY}} in the SVG
   */
  const generateLabelSvg = async (templateName: string, data: Record<string, string | number>) => {
    try {
      const response = await fetch(`/labels/${templateName}.svg`);
      if (!response.ok) throw new Error(`Template ${templateName} not found`);
      let svgContent = await response.text();

      // Process QR Codes if present in data
      // We look for any key that contains 'QRCode'
      const dataToInject = { ...data };

      for (const [key, value] of Object.entries(data)) {
        if (key.includes('QRCode') && value) {
          try {
            // Generate QR as SVG string
            const qrSvg = await QRCode.toString(String(value), {
              type: 'svg',
              margin: 0,
              color: {
                dark: '#000000',
                light: '#00000000' // transparent
              }
            });

            // Extract the path(s) from the generated SVG
            // QRCode.toString returns a full <svg>...<path d="..."/>...</svg>
            const pathMatch = qrSvg.match(/<path[^>]*\/>/g);
            if (pathMatch) {
              // Join all paths and wrap in a group that resets the coordinate system if needed
              // But usually, we'll just provide the path and let the template handle transform
              // We also need to extract the viewBox to know the size
              const viewBoxMatch = qrSvg.match(/viewBox="([^"]+)"/);
              let viewBox = '0 0 25 25';
              if (viewBoxMatch && viewBoxMatch[1]) {
                viewBox = viewBoxMatch[1];
              }
              const vparts = viewBox.split(' ').map(Number);
              const vw = vparts[2] || 25;
              const vh = vparts[3] || 25;

              // Return a group that scales the QR to a standard 100x100 internal units
              // or just the paths. Let's wrap in a g with the original viewBox
              dataToInject[key] = `<g transform="scale(${100 / vw}, ${100 / vh})">${pathMatch.join('')}</g>`;
            }
          } catch (qrErr) {
            console.error('QR Generation Error:', qrErr);
            dataToInject[key] = '';
          }
        }
      }

      // Replace placeholders {{KEY}} with dataToInject[KEY]
      Object.entries(dataToInject).forEach(([key, value]) => {
        const regex = new RegExp(`{{${key}}}`, 'g');
        svgContent = svgContent.replace(regex, String(value));
      });

      return svgContent;
    } catch (error) {
      console.error('Label Generation Error:', error);
      return null;
    }
  };

  /**
   * Triggers the browser print dialog for a specific SVG element/string
   */
  const printLabel = (svgHtml: string) => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    printWindow.document.write(`
      <html>
        <head>
          <title>Print Label</title>
          <style>
            @page { size: auto; margin: 0; }
            body { margin: 0; display: flex; justify-content: center; align-items: center; height: 100vh; }
            svg { width: 100%; height: auto; max-width: 400px; }
          </style>
        </head>
        <body>
          ${svgHtml}
          <script>
            window.onload = () => {
              window.print();
              setTimeout(() => window.close(), 500);
            };
          </script>
        </body>
      </html>
    `);
    printWindow.document.close();
  };

  return {
    generateLabelSvg,
    printLabel
  };
};
