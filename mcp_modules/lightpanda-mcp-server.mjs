#!/usr/bin/env node
/**
 * Lightpanda Headless Browser MCP Bridge for LibreChat.
 * Bridges stdio JSON-RPC protocol to the Lightpanda browser container.
 */
import http from "node:http";
import readline from "node:readline";

const LIGHTPANDA_URL = process.env.LIGHTPANDA_URL || "http://lightpanda:8765/mcp";

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false,
});

function postJsonRpc(bodyString) {
  return new Promise((resolve, reject) => {
    try {
      const targetUrl = new URL(LIGHTPANDA_URL);
      const req = http.request(
        {
          hostname: targetUrl.hostname,
          port: targetUrl.port || 8765,
          path: targetUrl.pathname,
          method: "POST",
          headers: {
            "Host": "127.0.0.1:8765",
            "Content-Type": "application/json",
            "Content-Length": Buffer.byteLength(bodyString),
          },
          timeout: 60000,
        },
        (res) => {
          let buffer = "";
          res.on("data", (chunk) => (buffer += chunk));
          res.on("end", () => resolve(buffer));
        }
      );

      req.on("timeout", () => {
        req.destroy(new Error("Request to Lightpanda browser timed out after 60s"));
      });

      req.on("error", (err) => reject(err));
      req.write(bodyString);
      req.end();
    } catch (err) {
      reject(err);
    }
  });
}

rl.on("line", async (line) => {
  const trimmed = line.trim();
  if (!trimmed) return;

  let parsed;
  try {
    parsed = JSON.parse(trimmed);
  } catch (err) {
    console.error("[Lightpanda MCP Bridge] Invalid JSON-RPC input:", err.message);
    return;
  }

  try {
    const response = await postJsonRpc(trimmed);
    if (response && response.trim()) {
      process.stdout.write(response.trim() + "\n");
    }
  } catch (err) {
    console.error(`[Lightpanda MCP Bridge Error]: ${err.message}`);
    if (parsed.id !== undefined && parsed.id !== null) {
      const errorResponse = JSON.stringify({
        jsonrpc: "2.0",
        id: parsed.id,
        error: {
          code: -32603,
          message: `Lightpanda browser error: ${err.message}`,
        },
      });
      process.stdout.write(errorResponse + "\n");
    }
  }
});

console.error("[Lightpanda MCP Bridge] Stdio bridge initialized for", LIGHTPANDA_URL);
