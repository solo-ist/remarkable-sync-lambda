/**
 * Lambda handler for reMarkable notebook sync.
 */

import type { APIGatewayProxyEventV2, APIGatewayProxyResultV2 } from "aws-lambda";
import { getApiKey, getRemarkableToken } from "./secrets.js";
import { RemarkableClient } from "./remarkable-client.js";

// Reuse client across invocations (Lambda container reuse)
let remarkableClient: RemarkableClient | null = null;

export async function handler(
  event: APIGatewayProxyEventV2
): Promise<APIGatewayProxyResultV2> {
  try {
    // Validate API key
    const providedKey = event.headers["x-api-key"] || event.headers["X-Api-Key"];
    const expectedKey = await getApiKey();

    if (!providedKey || providedKey !== expectedKey) {
      return errorResponse(401, "Invalid or missing API key");
    }

    // Check HTTP method
    const method = event.requestContext?.http?.method || "GET";
    if (method !== "POST") {
      return errorResponse(405, `Method ${method} not allowed. Use POST.`);
    }

    console.log("Starting notebook sync");

    // Initialize client lazily (reused across warm invocations)
    if (!remarkableClient) {
      const token = await getRemarkableToken();
      remarkableClient = new RemarkableClient(token);
    }

    // List all notebooks
    const notebooks = await remarkableClient.listNotebooks();
    console.log(`Found ${notebooks.length} items`);

    // Return notebook metadata
    const responseBody = {
      syncedAt: new Date().toISOString(),
      count: notebooks.length,
      items: notebooks,
    };

    return {
      statusCode: 200,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(responseBody, null, 2),
    };
  } catch (err) {
    console.error("Error during sync:", err);
    return errorResponse(500, err instanceof Error ? err.message : "Unknown error");
  }
}

function errorResponse(statusCode: number, message: string): APIGatewayProxyResultV2 {
  return {
    statusCode,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ error: message }),
  };
}
