/**
 * One-time script to register with reMarkable Cloud.
 *
 * Usage:
 *   1. Go to https://my.remarkable.com/device/desktop/connect
 *   2. Get a one-time code
 *   3. Run: npx ts-node scripts/register.ts YOUR_CODE
 *   4. Save the output token to Secrets Manager
 */

import { register } from "rmapi-js";

async function main() {
  const code = process.argv[2];

  if (!code) {
    console.error("Usage: npx ts-node scripts/register.ts <CODE>");
    console.error("");
    console.error("Get a code from: https://my.remarkable.com/device/desktop/connect");
    process.exit(1);
  }

  console.log(`Registering with code: ${code}`);

  try {
    const deviceToken = await register(code);
    console.log("");
    console.log("✅ Registration successful!");
    console.log("");
    console.log("Device token (save this to Secrets Manager):");
    console.log("─".repeat(60));
    console.log(deviceToken);
    console.log("─".repeat(60));
    console.log("");
    console.log("Run this command to store it:");
    console.log(`aws secretsmanager put-secret-value \\`);
    console.log(`  --secret-id remarkable-sync/rmapi-config \\`);
    console.log(`  --secret-string '${deviceToken}'`);
  } catch (err) {
    console.error("❌ Registration failed:", err);
    process.exit(1);
  }
}

main();
