#!/usr/bin/env node
/**
 * Free Web Scraper & DuckDuckGo Search MCP Server for LibreChat.
 * Requires 0 API keys. Provides search, reader-mode scraping, table extraction, and time grounding.
 */
import { McpServer } from "/app/mcp_modules/node_modules/@modelcontextprotocol/server/dist/index.mjs";
import { serveStdio } from "/app/mcp_modules/node_modules/@modelcontextprotocol/server/dist/stdio.mjs";
import { z } from "/app/mcp_modules/node_modules/zod/index.js";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const cheerio = require("cheerio");

const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36";

function cleanHtmlToMarkdown(html, baseUrl = "") {
  const $ = cheerio.load(html);

  // Remove non-content elements
  $("script, style, noscript, nav, footer, header, aside, svg, iframe, link, meta").remove();
  $("[aria-hidden=\"true\"], .cookie-banner, .advertisement, .ad-box, #cookie-notice").remove();

  const title = $("title").text().trim() || $("h1").first().text().trim() || "";

  // Helper to format nodes recursively
  function formatNode(node) {
    if (node.type === "text") {
      return node.data.replace(/\s+/g, " ");
    }
    if (node.type !== "tag") return "";

    const tag = node.name.toLowerCase();
    const children = $(node).contents().map((_, el) => formatNode(el)).get().join("");

    switch (tag) {
      case "h1":
        return `\n\n# ${children.trim()}\n\n`;
      case "h2":
        return `\n\n## ${children.trim()}\n\n`;
      case "h3":
        return `\n\n### ${children.trim()}\n\n`;
      case "h4":
      case "h5":
      case "h6":
        return `\n\n#### ${children.trim()}\n\n`;
      case "p":
        return `\n\n${children.trim()}\n\n`;
      case "br":
        return "\n";
      case "hr":
        return "\n\n---\n\n";
      case "b":
      case "strong":
        return `**${children.trim()}**`;
      case "i":
      case "em":
        return `*${children.trim()}*`;
      case "code":
        return `\`${children.trim()}\``;
      case "pre":
        return `\n\n\`\`\`\n${$(node).text().trim()}\n\`\`\`\n\n`;
      case "blockquote":
        return `\n\n> ${children.trim().replace(/\n/g, "\n> ")}\n\n`;
      case "li":
        return `\n* ${children.trim()}`;
      case "ul":
      case "ol":
        return `\n${children}\n`;
      case "a": {
        const text = children.trim() || $(node).attr("title") || "link";
        let href = $(node).attr("href");
        if (href) {
          try {
            href = new URL(href, baseUrl).toString();
            return `[${text}](${href})`;
          } catch {
            return text;
          }
        }
        return text;
      }
      case "table": {
        const rows = [];
        $(node).find("tr").each((_, tr) => {
          const cells = [];
          $(tr).find("th, td").each((_, td) => {
            cells.push($(td).text().trim().replace(/\|/g, "\\|"));
          });
          if (cells.length > 0) rows.push(cells);
        });
        if (rows.length === 0) return "";
        let mdTable = "\n\n| " + rows[0].join(" | ") + " |\n";
        mdTable += "| " + rows[0].map(() => "---").join(" | ") + " |\n";
        for (let i = 1; i < rows.length; i++) {
          mdTable += "| " + rows[i].join(" | ") + " |\n";
        }
        return mdTable + "\n\n";
      }
      default:
        return children;
    }
  }

  // Target main content container if present
  let root = $("article, main, #content, .content, #main, .post-content, .entry-content");
  if (root.length === 0) {
    root = $("body");
  }

  let markdown = formatNode(root[0] || $.root()[0]);
  // Collapse excessive newlines and whitespace
  markdown = markdown.replace(/\n{3,}/g, "\n\n").trim();

  return { title, markdown };
}

async function searchDuckDuckGo(query, maxResults = 5) {
  const url = `https://html.duckduckgo.com/html/?q=${encodeURIComponent(query)}`;
  const resp = await fetch(url, {
    headers: {
      "User-Agent": USER_AGENT,
      "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
      "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    },
  });

  if (!resp.ok) {
    throw new Error(`DuckDuckGo responded with status HTTP ${resp.status}`);
  }

  const html = await resp.text();
  const $ = cheerio.load(html);
  const results = [];

  $(".result").each((_, el) => {
    if (results.length >= maxResults) return false;
    const title = $(el).find(".result__title .result__a").text().trim();
    let link = $(el).find(".result__title .result__a").attr("href");
    if (link && link.includes("uddg=")) {
      const match = link.match(/uddg=([^&]+)/);
      if (match) {
        link = decodeURIComponent(match[1]);
      }
    }
    const snippet = $(el).find(".result__snippet").text().trim();
    if (title && link && !link.includes("duckduckgo.com/y.js")) {
      results.push({ title, link, snippet });
    }
  });

  return results;
}

function createServer() {
  const server = new McpServer({
    name: "free-web-scraper",
    version: "1.0.0",
  });

  // Tool 1: web_search (DuckDuckGo)
  server.registerTool("web_search", {
    title: "Web Search (DuckDuckGo)",
    description: "Search the web using DuckDuckGo with zero API keys. Returns top relevant search results with page titles, URLs, and descriptive summaries.",
    inputSchema: z.object({
      query: z.string().describe("The search query or keywords to look up."),
      max_results: z.number().optional().default(5).describe("Maximum number of results to return (1-15)."),
    }),
    outputSchema: z.object({
      query: z.string(),
      results: z.array(z.object({
        title: z.string(),
        link: z.string(),
        snippet: z.string(),
      })),
      total: z.number(),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  }, async ({ query, max_results }) => {
    try {
      const count = Math.max(1, Math.min(15, max_results || 5));
      const results = await searchDuckDuckGo(query, count);
      return {
        content: [{
          type: "text",
          text: results.length > 0
            ? results.map((r, i) => `${i + 1}. [${r.title}](${r.link})\n   ${r.snippet}`).join("\n\n")
            : "No results found for query.",
        }],
        structuredContent: { query, results, total: results.length },
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Search failed: ${err.message}` }],
        structuredContent: { query, results: [], total: 0, error: err.message },
      };
    }
  });

  // Tool 2: scrape_webpage
  server.registerTool("scrape_webpage", {
    title: "Scrape Webpage (Reader Mode)",
    description: "Fetch and scrape the main content of any webpage URL, converting it into clean, clutter-free Markdown. Strips navigation, headers, footers, and ads.",
    inputSchema: z.object({
      url: z.string().describe("The full HTTP or HTTPS URL of the webpage to scrape."),
      max_length: z.number().optional().default(10000).describe("Maximum character length of the returned markdown (default: 10,000)."),
    }),
    outputSchema: z.object({
      url: z.string(),
      title: z.string(),
      markdown: z.string(),
      truncated: z.boolean(),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  }, async ({ url, max_length }) => {
    try {
      const resp = await fetch(url, {
        headers: {
          "User-Agent": USER_AGENT,
          "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
      });

      if (!resp.ok) {
        throw new Error(`Target responded with HTTP ${resp.status} ${resp.statusText}`);
      }

      const html = await resp.text();
      const { title, markdown: rawMd } = cleanHtmlToMarkdown(html, url);

      const limit = max_length || 10000;
      const truncated = rawMd.length > limit;
      const markdown = truncated ? rawMd.slice(0, limit) + "\n\n*(Content truncated for length)*" : rawMd;

      const header = `# ${title || "Page Content"}\nURL: ${url}\n\n`;
      return {
        content: [{ type: "text", text: header + markdown }],
        structuredContent: { url, title, markdown, truncated },
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Scraping failed for ${url}: ${err.message}` }],
        structuredContent: { url, title: "", markdown: "", truncated: false, error: err.message },
      };
    }
  });

  // Tool 3: extract_tables
  server.registerTool("extract_tables", {
    title: "Extract Tables",
    description: "Extract structured data tables from a webpage into clean Markdown tables.",
    inputSchema: z.object({
      url: z.string().describe("The webpage URL containing data tables."),
    }),
    outputSchema: z.object({
      url: z.string(),
      tables_found: z.number(),
      markdown_tables: z.array(z.string()),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  }, async ({ url }) => {
    try {
      const resp = await fetch(url, { headers: { "User-Agent": USER_AGENT } });
      const html = await resp.text();
      const $ = cheerio.load(html);
      const tables = [];

      $("table").each((i, table) => {
        const rows = [];
        $(table).find("tr").each((_, tr) => {
          const cells = [];
          $(tr).find("th, td").each((_, td) => {
            cells.push($(td).text().trim().replace(/\|/g, "\\|").replace(/\s+/g, " "));
          });
          if (cells.length > 0) rows.push(cells);
        });

        if (rows.length > 0) {
          let md = `### Table ${i + 1}\n| ` + rows[0].join(" | ") + " |\n";
          md += "| " + rows[0].map(() => "---").join(" | ") + " |\n";
          for (let r = 1; r < rows.length; r++) {
            md += "| " + rows[r].join(" | ") + " |\n";
          }
          tables.push(md);
        }
      });

      return {
        content: [{
          type: "text",
          text: tables.length > 0 ? tables.join("\n\n") : "No HTML tables found on the page.",
        }],
        structuredContent: { url, tables_found: tables.length, markdown_tables: tables },
      };
    } catch (err) {
      return {
        content: [{ type: "text", text: `Table extraction failed: ${err.message}` }],
        structuredContent: { url, tables_found: 0, markdown_tables: [], error: err.message },
      };
    }
  });

  // Tool 4: get_current_time
  server.registerTool("get_current_time", {
    title: "Current Time & Timezone",
    description: "Get real-world current date, time, and timezone information (UTC and WIB/GMT+7) for temporal accuracy.",
    inputSchema: z.object({}),
    outputSchema: z.object({
      utc: z.string(),
      wib: z.string(),
      day_of_week: z.string(),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  }, async () => {
    const now = new Date();
    const utc = now.toISOString();
    const wib = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Jakarta",
      dateStyle: "full",
      timeStyle: "long",
    }).format(now);
    const day_of_week = new Intl.DateTimeFormat("en-US", {
      timeZone: "Asia/Jakarta",
      weekday: "long",
    }).format(now);

    const text = `Current Local Time (WIB / GMT+7): ${wib}\nUTC: ${utc}\nDay: ${day_of_week}`;
    return {
      content: [{ type: "text", text }],
      structuredContent: { utc, wib, day_of_week },
    };
  });

  return server;
}

export async function main() {
  const handle = serveStdio(() => createServer(), {
    onerror: (err) => {
      console.error("[Scraper MCP Server Error]:", err);
    },
  });
  console.error("Scraper MCP Server running on stdio");
  return handle;
}

main().catch((err) => {
  console.error("Fatal error in scraper-mcp-server main():", err);
  process.exit(1);
});
