/**
 * AWS Secrets Manager integration.
 */

import {
  SecretsManagerClient,
  GetSecretValueCommand,
} from "@aws-sdk/client-secrets-manager";

const client = new SecretsManagerClient({});

// Cache secrets to avoid repeated API calls within same Lambda invocation
let cachedApiKey: string | null = null;
let cachedRemarkableToken: string | null = null;

export async function getApiKey(): Promise<string> {
  if (cachedApiKey) return cachedApiKey;

  const secretArn = process.env.API_KEY_SECRET_ARN;
  if (!secretArn) {
    // Fallback for local testing
    const envKey = process.env.API_KEY;
    if (envKey) return envKey;
    throw new Error("API_KEY_SECRET_ARN not configured");
  }

  const response = await client.send(
    new GetSecretValueCommand({ SecretId: secretArn })
  );

  cachedApiKey = response.SecretString || "";
  return cachedApiKey;
}

export async function getRemarkableToken(): Promise<string> {
  if (cachedRemarkableToken) return cachedRemarkableToken;

  const secretArn = process.env.RMAPI_CONFIG_SECRET_ARN;
  if (!secretArn) {
    throw new Error("RMAPI_CONFIG_SECRET_ARN not configured");
  }

  const response = await client.send(
    new GetSecretValueCommand({ SecretId: secretArn })
  );

  cachedRemarkableToken = response.SecretString || "";
  return cachedRemarkableToken;
}
