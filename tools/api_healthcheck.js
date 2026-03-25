/**
 * Simple API healthcheck script (Node.js).
 *
 * Example:
 *   node tools/api_healthcheck.js http://localhost:8000/health
 */

const url = process.argv[2] || "http://localhost:8000/health";

async function main() {
  try {
    const res = await fetch(url);
    const json = await res.json();
    console.log(JSON.stringify(json, null, 2));
    if (!res.ok) process.exitCode = 1;
  } catch (err) {
    console.error("Healthcheck failed:", err);
    process.exitCode = 1;
  }
}

main();

