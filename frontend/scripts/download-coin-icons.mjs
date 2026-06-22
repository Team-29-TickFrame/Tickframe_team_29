import { mkdir, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const outDir = join(scriptDir, "..", "public", "assets", "coins");

const logos = {
  btc: "https://cryptologos.cc/logos/bitcoin-btc-logo.png?v=040",
  eth: "https://cryptologos.cc/logos/ethereum-eth-logo.png?v=040",
  sol: "https://cryptologos.cc/logos/solana-sol-logo.png?v=040",
  xrp: "https://cryptologos.cc/logos/xrp-xrp-logo.png?v=040",
  avax: "https://cryptologos.cc/logos/avalanche-avax-logo.png?v=040",
  ton: "https://cryptologos.cc/logos/toncoin-ton-logo.png?v=040",
  trx: "https://cryptologos.cc/logos/tron-trx-logo.png?v=040",
  bonk: "https://cryptologos.cc/logos/bonk1-bonk-logo.png?v=040",
  floki: "https://cryptologos.cc/logos/floki-inu-floki-logo.png?v=040",
};

await mkdir(outDir, { recursive: true });

for (const [symbol, url] of Object.entries(logos)) {
  const response = await fetch(url, {
    headers: { "user-agent": "Tickframe asset sync" },
  });
  if (!response.ok) {
    throw new Error(`Failed to download ${symbol}: ${response.status} ${url}`);
  }
  const data = new Uint8Array(await response.arrayBuffer());
  await writeFile(join(outDir, `${symbol}.png`), data);
  console.log(`${symbol}: ${data.byteLength} bytes`);
}

console.log("PENGU is not available on CryptoLogos yet; keep pengu.png as a local fallback.");
