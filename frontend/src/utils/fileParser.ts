function normalizeTexts(values: string[]): string[] {
  return values.map((item) => item.trim()).filter(Boolean);
}

function splitTextFile(content: string): string[] {
  return normalizeTexts(content.split(/\r?\n+/));
}

function parseCsvRows(content: string): string[][] {
  const rows: string[][] = [];
  let currentCell = "";
  let currentRow: string[] = [];
  let inQuotes = false;

  for (let index = 0; index < content.length; index += 1) {
    const char = content[index];
    const nextChar = content[index + 1];

    if (char === "\"") {
      if (inQuotes && nextChar === "\"") {
        currentCell += "\"";
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }

    if (char === "," && !inQuotes) {
      currentRow.push(currentCell);
      currentCell = "";
      continue;
    }

    if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && nextChar === "\n") {
        index += 1;
      }
      currentRow.push(currentCell);
      rows.push(currentRow);
      currentCell = "";
      currentRow = [];
      continue;
    }

    currentCell += char;
  }

  if (currentCell || currentRow.length > 0) {
    currentRow.push(currentCell);
    rows.push(currentRow);
  }

  return rows;
}

function extractTextsFromCsv(content: string): string[] {
  const rows = parseCsvRows(content).filter((row) => row.some((cell) => cell.trim()));
  if (rows.length === 0) {
    return [];
  }

  const headerRow = rows[0].map((cell) => cell.trim().toLowerCase());
  const textColumnIndex = headerRow.findIndex((cell) => ["text", "内容", "文本"].includes(cell));
  const bodyRows = textColumnIndex >= 0 ? rows.slice(1) : rows;

  if (textColumnIndex >= 0) {
    return normalizeTexts(bodyRows.map((row) => row[textColumnIndex] ?? ""));
  }

  return normalizeTexts(bodyRows.map((row) => row.find((cell) => cell.trim()) ?? ""));
}

export async function extractTextsFromFile(file: File): Promise<string[]> {
  const content = await file.text();
  const extension = file.name.split(".").pop()?.toLowerCase();

  if (extension === "txt") {
    return splitTextFile(content);
  }

  if (extension === "csv") {
    return extractTextsFromCsv(content);
  }

  throw new Error("当前仅支持导入 TXT 或 CSV 文件。");
}
