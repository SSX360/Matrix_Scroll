import { readFileSync } from "node:fs"

function asciiJsonString(value) {
  return JSON.stringify(value).replace(/[\u007f-\uffff]/g, (char) => {
    return "\\u" + char.charCodeAt(0).toString(16).padStart(4, "0")
  })
}

function stableStringify(value) {
  if (value === null) {
    return "null"
  }
  if (Array.isArray(value)) {
    return `[${value.map(stableStringify).join(",")}]`
  }
  if (typeof value === "object") {
    return `{${Object.keys(value)
      .sort()
      .map((key) => `${asciiJsonString(key)}:${stableStringify(value[key])}`)
      .join(",")}}`
  }
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new Error("Manifest contains NaN or Infinity, which Matrix Scroll rejects.")
    }
    return JSON.stringify(value)
  }
  return asciiJsonString(value)
}

export function canonicalBytes(manifest) {
  const body = {}
  Object.keys(manifest).forEach((key) => {
    if (key !== "signature") {
      body[key] = manifest[key]
    }
  })
  return new TextEncoder().encode(stableStringify(body))
}

if (process.argv[2]) {
  const manifest = JSON.parse(readFileSync(process.argv[2], "utf8"))
  process.stdout.write(Buffer.from(canonicalBytes(manifest)).toString("hex"))
}
