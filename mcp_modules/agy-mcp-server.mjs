#!/usr/bin/env node
import { McpServer } from "/app/mcp_modules/node_modules/@modelcontextprotocol/server/dist/index.mjs";
import { serveStdio } from "/app/mcp_modules/node_modules/@modelcontextprotocol/server/dist/stdio.mjs";
import { z } from "/app/mcp_modules/node_modules/zod/index.js";

const GUARDRAIL_URL = process.env.AGY_GUARDRAIL_URL || "http://172.18.0.1:8999";

async function postJson(endpoint, data) {
  const resp = await fetch(`${GUARDRAIL_URL}${endpoint}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  const json = await resp.json();
  return { status: resp.status, data: json };
}

async function getJson(endpoint) {
  const resp = await fetch(`${GUARDRAIL_URL}${endpoint}`);
  const json = await resp.json();
  return { status: resp.status, data: json };
}

function createServer() {
  const server = new McpServer({
    name: "agy-vps-guardrail",
    version: "1.0.0",
  });

  server.registerTool("agy_vps_status", {
    title: "AGY VPS Status",
    description: "Retrieve real-time VPS health, uptime, disk space, and memory metrics.",
    inputSchema: z.object({}),
    outputSchema: z.object({
      status: z.string(),
      uptime: z.string().optional(),
      disk_root: z.string().optional(),
      memory: z.string().optional(),
      error: z.string().optional(),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  }, async () => {
    try {
      const res = await getJson("/vps/status");
      return {
        content: [{ type: "text", text: JSON.stringify(res.data, null, 2) }],
        structuredContent: res.data,
      };
    } catch (e) {
      return {
        content: [{ type: "text", text: `Failed to fetch VPS status: ${e.message}` }],
        structuredContent: { status: "error", error: e.message },
      };
    }
  });

  server.registerTool("agy_classify_command", {
    title: "AGY Classify Command",
    description: "Classify a system command through the 3-Tier Guardrail Engine without executing it.",
    inputSchema: z.object({
      command: z.string().describe("The shell command to test for safety classification."),
    }),
    outputSchema: z.object({
      tier: z.number(),
      action: z.string(),
      reason: z.string(),
      safe: z.boolean(),
    }),
    annotations: {
      readOnlyHint: true,
      destructiveHint: false,
    },
  }, async ({ command }) => {
    try {
      const res = await postJson("/classify", { command });
      return {
        content: [{ type: "text", text: JSON.stringify(res.data, null, 2) }],
        structuredContent: res.data,
      };
    } catch (e) {
      return {
        content: [{ type: "text", text: `Failed to classify command: ${e.message}` }],
        structuredContent: { tier: 3, action: "ERROR", reason: e.message, safe: false },
      };
    }
  });

  server.registerTool("agy_execute_command", {
    title: "AGY Execute Command",
    description: "Execute a bash command on the VPS host with 3-Tier Guardrail protection.",
    inputSchema: z.object({
      command: z.string().describe("The shell command to execute on the VPS."),
      rationale: z.string().describe("Explanation of why this command is being executed (logged for audit)."),
      force_confirm: z.boolean().optional().default(false).describe("Set to true to confirm execution if the command is classified as Tier 3 Destructive."),
    }),
    outputSchema: z.object({
      ok: z.boolean(),
      tier: z.number().optional(),
      stdout: z.string().optional(),
      stderr: z.string().optional(),
      returncode: z.number().optional(),
      blocked: z.boolean().optional(),
      error: z.string().optional(),
      reason: z.string().optional(),
    }),
    annotations: {
      readOnlyHint: false,
      destructiveHint: true,
    },
  }, async ({ command, rationale, force_confirm }) => {
    try {
      const res = await postJson("/exec", { command, rationale, force_confirm });
      const text = res.data.stdout || res.data.stderr || res.data.error || res.data.reason || JSON.stringify(res.data);
      return {
        content: [{ type: "text", text }],
        structuredContent: res.data,
      };
    } catch (e) {
      return {
        content: [{ type: "text", text: `Execution failed: ${e.message}` }],
        structuredContent: { ok: false, error: e.message },
      };
    }
  });

  server.registerTool("agy_run_agent", {
    title: "AGY Autonomous Agent Run",
    description: "Execute a task with the Google Antigravity (AGY) agent CLI on the VPS host.",
    inputSchema: z.object({
      prompt: z.string().describe("Detailed prompt or instructions for the AGY agent to perform."),
      auto_approve: z.boolean().optional().default(true).describe("Auto-approve agent tool permissions during execution."),
    }),
    outputSchema: z.object({
      ok: z.boolean(),
      output: z.string().optional(),
      error: z.string().optional(),
      exit_code: z.number().optional(),
    }),
    annotations: {
      readOnlyHint: false,
      destructiveHint: true,
    },
  }, async ({ prompt, auto_approve }) => {
    try {
      const res = await postJson("/agy", { prompt, auto_approve });
      return {
        content: [{ type: "text", text: res.data.output || res.data.error || "Execution finished." }],
        structuredContent: res.data,
      };
    } catch (e) {
      return {
        content: [{ type: "text", text: `AGY agent run failed: ${e.message}` }],
        structuredContent: { ok: false, error: e.message },
      };
    }
  });

  return server;
}

export async function main() {
  const handle = serveStdio(() => createServer(), {
    onerror: (err) => {
      console.error("AGY MCP Server Error:", err);
    },
  });
  console.error("AGY Guardrail MCP Server running on stdio");
  return handle;
}

main().catch((err) => {
  console.error("Fatal error in agy-mcp-server main():", err);
  process.exit(1);
});
