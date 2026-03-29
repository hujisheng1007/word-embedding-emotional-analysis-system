import type { ImportSummary } from "../types/analysis";

export interface ParsedImportResult {
  texts: string[];
  summary: ImportSummary;
}

function normalizeText(value: string): string {
  return value.replace(/\u3000/g, " ").replace(/\s+/g, " ").trim();
}

function uniqueTexts(values: string[]): { texts: string[]; duplicatesRemoved: number } {
  const seen = new Set<string>();
  const texts: string[] = [];
  let duplicatesRemoved = 0;

  values.forEach((value) => {
    if (seen.has(value)) {
      duplicatesRemoved += 1;
      return;
    }
    seen.add(value);
    texts.push(value);
  });

  return { texts, duplicatesRemoved };
}

function splitTextFile(content: string): ParsedImportResult {
  const entries = content.split(/\r?\n+/).map((item) => normalizeText(item));
  const emptyRemoved = entries.filter((item) => !item).length;
  const normalized = entries.filter(Boolean);
  const { texts, duplicatesRemoved } = uniqueTexts(normalized);

  return {
    texts,
    summary: {
      total_entries: normalized.length + emptyRemoved,
      extracted_count: texts.length,
      duplicates_removed: duplicatesRemoved,
      empty_removed: emptyRemoved,
      detected_column: null,
      file_type: "txt"
    }
  };
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

function extractTextsFromCsv(content: string): ParsedImportResult {
  const rows = parseCsvRows(content).filter((row) => row.some((cell) => cell.trim()));
  if (rows.length === 0) {
    return {
      texts: [],
      summary: {
        total_entries: 0,
        extracted_count: 0,
        duplicates_removed: 0,
        empty_removed: 0,
        detected_column: null,
        file_type: "csv"
      }
    };
  }

  const headerRow = rows[0].map((cell) => cell.trim());
  const headerMap = headerRow.map((cell) => cell.toLowerCase());
  const candidates = ["text", "文本", "内容", "body", "message", "comment"];
  const textColumnIndex = headerMap.findIndex((cell) => candidates.includes(cell));
  const bodyRows = textColumnIndex >= 0 ? rows.slice(1) : rows;
  const rawTexts = bodyRows.map((row) =>
    textColumnIndex >= 0 ? row[textColumnIndex] ?? "" : row.find((cell) => cell.trim()) ?? ""
  );
  const normalizedTexts = rawTexts.map((item) => normalizeText(item));
  const emptyRemoved = normalizedTexts.filter((item) => !item).length;
  const filteredTexts = normalizedTexts.filter(Boolean);
  const { texts, duplicatesRemoved } = uniqueTexts(filteredTexts);

  return {
    texts,
    summary: {
      total_entries: bodyRows.length,
      extracted_count: texts.length,
      duplicates_removed: duplicatesRemoved,
      empty_removed: emptyRemoved,
      detected_column: textColumnIndex >= 0 ? headerRow[textColumnIndex] ?? null : null,
      file_type: "csv"
    }
  };
}

export async function extractTextsFromFile(file: File): Promise<ParsedImportResult> {
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
