#!/usr/bin/env node
import { McpServer } from "/app/mcp_modules/node_modules/@modelcontextprotocol/server/dist/index.mjs";
import { serveStdio } from "/app/mcp_modules/node_modules/@modelcontextprotocol/server/dist/stdio.mjs";
import { z } from "/app/mcp_modules/node_modules/zod/index.js";
import fs from "fs/promises";
import path from "path";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
let marked;
try {
  const markedPkg = require("/app/node_modules/marked");
  marked = markedPkg.marked || markedPkg;
} catch (e) {
  console.error("Warning: Could not load marked:", e.message);
}

const GOTENBERG_URL = process.env.GOTENBERG_URL || "http://gotenberg:3000";
const OUTPUT_DIR = process.env.PDF_OUTPUT_DIR || "/app/pdf_output";
const PUBLIC_BASE_URL = process.env.PUBLIC_PDF_URL_BASE || "https://ai.bule.my.id/pdf";

const THEMES = {
  modern: `
    @page {
      size: A4;
      margin: 20mm;
    }
    *, *::before, *::after {
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
      color: #1e293b;
      background: #ffffff;
      line-height: 1.65;
      font-size: 10.5pt;
      margin: 0;
      padding: 0;
    }
    h1, h2, h3, h4, h5, h6 {
      color: #0f172a;
      font-weight: 700;
      line-height: 1.25;
      margin-top: 1.4em;
      margin-bottom: 0.6em;
      page-break-after: avoid;
    }
    h1 {
      font-size: 22pt;
      color: #1e40af;
      border-bottom: 2px solid #3b82f6;
      padding-bottom: 8px;
      margin-top: 0;
    }
    h2 {
      font-size: 15pt;
      color: #1e3a8a;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
    }
    h3 {
      font-size: 12pt;
      color: #2563eb;
    }
    p {
      margin: 0.8em 0;
    }
    a {
      color: #2563eb;
      text-decoration: underline;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.2em 0;
      font-size: 9.5pt;
      page-break-inside: avoid;
    }
    th, td {
      border: 1px solid #cbd5e1;
      padding: 8px 12px;
      text-align: left;
    }
    th {
      background: #f1f5f9;
      color: #0f172a;
      font-weight: 600;
    }
    tr:nth-child(even) td {
      background: #f8fafc;
    }
    blockquote {
      margin: 1.2em 0;
      padding: 10px 18px;
      background: #eff6ff;
      border-left: 4px solid #3b82f6;
      border-radius: 0 8px 8px 0;
      color: #1e3a8a;
      page-break-inside: avoid;
    }
    blockquote p {
      margin: 0.3em 0;
    }
    code {
      font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 9pt;
      background: #f1f5f9;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid #e2e8f0;
      color: #0f172a;
    }
    pre {
      background: #0f172a;
      color: #f8fafc;
      padding: 14px;
      border-radius: 6px;
      overflow-x: auto;
      page-break-inside: avoid;
      font-size: 9pt;
      line-height: 1.45;
    }
    pre code {
      background: transparent;
      color: inherit;
      padding: 0;
      border: none;
    }
    ul, ol {
      margin: 0.8em 0;
      padding-left: 24px;
    }
    li {
      margin-bottom: 0.4em;
    }
    hr {
      border: none;
      border-top: 1px solid #e2e8f0;
      margin: 1.8em 0;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      font-size: 8pt;
      font-weight: 600;
      border-radius: 9999px;
      background: #e0e7ff;
      color: #3730a3;
    }
  `,
  report: `
    @page {
      size: A4;
      margin: 22mm 18mm;
    }
    *, *::before, *::after {
      box-sizing: border-box;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      color: #111827;
      line-height: 1.7;
      font-size: 10pt;
      margin: 0;
    }
    .report-header {
      border-bottom: 3px solid #0f172a;
      padding-bottom: 15px;
      margin-bottom: 25px;
    }
    .report-title {
      font-size: 24pt;
      font-weight: 800;
      color: #0f172a;
      margin: 0 0 6px 0;
    }
    .report-subtitle {
      font-size: 11pt;
      color: #64748b;
      margin: 0;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    h1, h2, h3 {
      color: #0f172a;
      font-weight: 700;
      page-break-after: avoid;
    }
    h1 { font-size: 18pt; margin-top: 1.5em; border-bottom: 1.5px solid #0f172a; padding-bottom: 6px; }
    h2 { font-size: 13pt; margin-top: 1.2em; color: #1e293b; }
    h3 { font-size: 11pt; color: #334155; }
    table {
      width: 100%;
      border-collapse: collapse;
      margin: 1.5em 0;
      page-break-inside: avoid;
      font-size: 9.5pt;
    }
    th, td {
      padding: 9px 12px;
      text-align: left;
      border-bottom: 1px solid #e2e8f0;
    }
    th {
      background: #0f172a;
      color: #ffffff;
      font-weight: 600;
      text-transform: uppercase;
      font-size: 8.5pt;
      letter-spacing: 0.05em;
    }
    tr:nth-child(even) td {
      background: #f8fafc;
    }
    blockquote {
      border-left: 4px solid #0f172a;
      padding: 8px 16px;
      margin: 1.2em 0;
      background: #f8fafc;
      font-style: italic;
    }
  `,
  minimal: `
    @page {
      size: A4;
      margin: 20mm;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
      color: #000000;
      line-height: 1.6;
      font-size: 10pt;
    }
    h1, h2, h3 {
      color: #000000;
      page-break-after: avoid;
    }
    h1 { font-size: 20pt; border-bottom: 1px solid #000000; padding-bottom: 6px; }
    h2 { font-size: 14pt; border-bottom: 1px solid #cccccc; padding-bottom: 4px; }
    table { width: 100%; border-collapse: collapse; margin: 1em 0; page-break-inside: avoid; }
    th, td { border: 1px solid #999999; padding: 6px 10px; text-align: left; font-size: 9pt; }
    th { background: #eeeeee; font-weight: bold; }
    pre, code { font-family: monospace; font-size: 9pt; }
    pre { border: 1px solid #cccccc; padding: 10px; background: #fafafa; }
  `,
  academic: `
    @page {
      size: A4;
      margin: 25mm 25mm 25mm 25mm;
    }
    body {
      font-family: "Times New Roman", Times, Georgia, serif;
      color: #111111;
      line-height: 1.7;
      font-size: 11pt;
      text-align: justify;
    }
    h1, h2, h3 {
      font-family: "Times New Roman", Times, Georgia, serif;
      color: #000000;
      text-align: left;
      page-break-after: avoid;
    }
    h1 { font-size: 18pt; text-align: center; margin-bottom: 1.5em; font-weight: bold; }
    h2 { font-size: 13pt; margin-top: 1.5em; font-weight: bold; border-bottom: 1px solid #ccc; padding-bottom: 3px; }
    h3 { font-size: 11pt; font-style: italic; }
    p { text-indent: 1.5em; margin: 0.4em 0; }
    table { width: 100%; border-top: 2px solid #000; border-bottom: 2px solid #000; border-collapse: collapse; margin: 1.5em 0; page-break-inside: avoid; }
    th { border-bottom: 1px solid #000; padding: 6px 8px; font-weight: bold; text-align: left; }
    td { padding: 6px 8px; border: none; }
    blockquote { margin: 1em 2em; font-style: italic; }
  `
};

function formatHeaderFooter(content, title) {
  if (!content) return null;
  return `<!DOCTYPE html>
<html>
<head>
  <style>
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 8pt;
      color: #64748b;
      margin: 0;
      padding: 0 10mm;
      width: 100%;
      box-sizing: border-box;
    }
    .flex-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
    }
    .flex-footer {
      display: flex;
      justify-content: space-between;
      align-items: center;
      width: 100%;
      border-top: 1px solid #e2e8f0;
      padding-top: 4px;
    }
  </style>
</head>
<body>
  ${content.replace("{{title}}", title || "")}
</body>
</html>`;
}

function assembleHtmlDocument({ html, markdown, title, theme, customCss }) {
  let bodyContent = html || "";

  if (!bodyContent && markdown && marked) {
    bodyContent = marked.parse(markdown);
  } else if (!bodyContent && markdown) {
    bodyContent = `<pre>${markdown}</pre>`;
  }

  if (bodyContent.trim().toLowerCase().startsWith("<!doctype html") || bodyContent.trim().toLowerCase().startsWith("<html")) {
    return bodyContent;
  }

  const selectedThemeCss = THEMES[theme] || THEMES.modern;

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${title || "Document"}</title>
  <style>
    ${selectedThemeCss}
    ${customCss || ""}
  </style>
</head>
<body>
  ${bodyContent}
</body>
</html>`;
}

function createServer() {
  const server = new McpServer({
    name: "pdf-generator",
    version: "1.0.0",
  });

  server.registerTool("generate_pdf", {
    title: "Generate PDF with CSS Styling & Print Formatting",
    description: "Compiles HTML or Markdown into a publication-quality PDF using headless Chromium. Fully supports modern CSS3, @page, flexbox, tables, custom styling, running headers, footers with page numbers, and custom themes (modern, report, minimal, academic). Returns a direct download link.",
    inputSchema: z.object({
      html: z.string().optional().describe("HTML markup with full CSS styling (<style> or inline). If provided, takes precedence over markdown."),
      markdown: z.string().optional().describe("Markdown content. Automatically rendered into styled HTML if html is omitted."),
      title: z.string().optional().describe("Document title for metadata and running header."),
      filename: z.string().optional().describe("Desired PDF filename (e.g., financial-report.pdf, invoice-101.pdf)."),
      theme: z.enum(["modern", "report", "minimal", "academic"]).optional().default("modern").describe("Pre-built print CSS theme: modern, report, minimal, academic. Default: modern."),
      custom_css: z.string().optional().describe("Additional custom CSS styling rules to inject into the document head."),
      paper_size: z.enum(["A4", "Letter"]).optional().default("A4").describe("Paper size: A4 (default) or Letter."),
      landscape: z.boolean().optional().default(false).describe("Orientation: true for landscape, false for portrait (default)."),
      margin_top: z.string().optional().default("20mm").describe("Top margin (e.g. 20mm, 0.8in). Default: 20mm."),
      margin_bottom: z.string().optional().default("20mm").describe("Bottom margin (e.g. 20mm, 0.8in). Default: 20mm."),
      margin_left: z.string().optional().default("20mm").describe("Left margin (e.g. 20mm, 0.8in). Default: 20mm."),
      margin_right: z.string().optional().default("20mm").describe("Right margin (e.g. 20mm, 0.8in). Default: 20mm."),
      header_html: z.string().optional().describe("Optional HTML for running page header."),
      footer_html: z.string().optional().describe("Optional HTML for running page footer. Gotenberg supports <span class=\"pageNumber\"></span> and <span class=\"totalPages\"></span>."),
      include_default_header_footer: z.boolean().optional().default(true).describe("If true and no custom header/footer is specified, automatically generates clean running header with title and footer with page numbers.")
    }),
    outputSchema: z.object({
      ok: z.boolean(),
      download_url: z.string().optional(),
      filename: z.string().optional(),
      filesize_bytes: z.number().optional(),
      error: z.string().optional()
    })
  }, async (args) => {
    try {
      const {
        html,
        markdown,
        title = "Document",
        theme = "modern",
        custom_css,
        paper_size = "A4",
        landscape = false,
        margin_top = "20mm",
        margin_bottom = "20mm",
        margin_left = "20mm",
        margin_right = "20mm",
        include_default_header_footer = true
      } = args;

      if (!html && !markdown) {
        return {
          content: [{ type: "text", text: "Error: Either html or markdown must be provided." }],
          structuredContent: { ok: false, error: "Either html or markdown must be provided." }
        };
      }

      const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
      let safeFilename = args.filename ? args.filename.replace(/[^a-zA-Z0-9_\-\.]/g, "_") : `document-${timestamp}.pdf`;
      if (!safeFilename.toLowerCase().endsWith(".pdf")) {
        safeFilename += ".pdf";
      }

      const fullHtml = assembleHtmlDocument({ html, markdown, title, theme, customCss: custom_css });

      let effectiveHeader = args.header_html;
      let effectiveFooter = args.footer_html;

      if (!effectiveHeader && include_default_header_footer) {
        effectiveHeader = `<div class="flex-row"><span>${title}</span><span>${new Date().toLocaleDateString()}</span></div>`;
      }
      if (!effectiveFooter && include_default_header_footer) {
        effectiveFooter = `<div class="flex-footer"><span>LibreChat Document Output</span><span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span></div>`;
      }

      const formattedHeader = formatHeaderFooter(effectiveHeader, title);
      const formattedFooter = formatHeaderFooter(effectiveFooter, title);

      const form = new FormData();
      form.append("files", new Blob([fullHtml], { type: "text/html" }), "index.html");

      if (formattedHeader) {
        form.append("files", new Blob([formattedHeader], { type: "text/html" }), "header.html");
      }
      if (formattedFooter) {
        form.append("files", new Blob([formattedFooter], { type: "text/html" }), "footer.html");
      }

      if (paper_size === "Letter") {
        form.append("paperWidth", "8.5in");
        form.append("paperHeight", "11in");
      } else {
        form.append("paperWidth", "8.27in");
        form.append("paperHeight", "11.7in");
      }

      form.append("marginTop", margin_top);
      form.append("marginBottom", margin_bottom);
      form.append("marginLeft", margin_left);
      form.append("marginRight", margin_right);

      if (landscape) {
        form.append("landscape", "true");
      }
      form.append("printBackground", "true");

      const gotenbergEndpoint = `${GOTENBERG_URL}/forms/chromium/convert/html`;
      const resp = await fetch(gotenbergEndpoint, {
        method: "POST",
        body: form
      });

      if (!resp.ok) {
        const errorText = await resp.text();
        throw new Error(`Gotenberg conversion failed (status ${resp.status}): ${errorText}`);
      }

      const arrayBuffer = await resp.arrayBuffer();
      const buffer = Buffer.from(arrayBuffer);

      await fs.mkdir(OUTPUT_DIR, { recursive: true });
      const outputPath = path.join(OUTPUT_DIR, safeFilename);
      await fs.writeFile(outputPath, buffer);

      const downloadUrl = `${PUBLIC_BASE_URL}/${safeFilename}`;
      const sizeKb = (buffer.length / 1024).toFixed(1);

      const markdownResult = `### 📄 PDF Generated Successfully!
- **File:** [${safeFilename}](${downloadUrl})
- **Size:** ${sizeKb} KB
- **Format:** ${paper_size} (${landscape ? "Landscape" : "Portrait"}), Theme: \`${theme}\`

👉 **[Click Here to View or Download Your PDF](${downloadUrl})**`;

      return {
        content: [{ type: "text", text: markdownResult }],
        structuredContent: {
          ok: true,
          download_url: downloadUrl,
          filename: safeFilename,
          filesize_bytes: buffer.length
        }
      };

    } catch (err) {
      console.error("[PDF_MCP_ERROR]", err);
      return {
        content: [{ type: "text", text: `PDF generation failed: ${err.message}` }],
        structuredContent: { ok: false, error: err.message }
      };
    }
  });

  return server;
}

export async function main() {
  const handle = serveStdio(() => createServer(), {
    onerror: (err) => {
      console.error("PDF MCP Server Error:", err);
    },
  });
  console.error("PDF Generator MCP Server running on stdio");
  return handle;
}

main().catch((err) => {
  console.error("Fatal error in pdf-generator-mcp-server main():", err);
  process.exit(1);
});
