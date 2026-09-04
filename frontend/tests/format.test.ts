import { describe, expect, it } from "vitest";
import { fmtMoney, fmtNumber, fmtPct, fmtDelta, titleCase, DOC_TYPE_LABELS } from "@/lib/format";

describe("fmtMoney", () => {
  it("formats millions with currency suffix", () => {
    expect(fmtMoney(630.4)).toMatch(/630\.4/);
    expect(fmtMoney(null)).toBe("—");
    expect(fmtMoney(undefined)).toBe("—");
  });
});

describe("fmtNumber / fmtPct", () => {
  it("handles nulls and decimals", () => {
    expect(fmtNumber(1.234, 2)).toBe("1.23");
    expect(fmtNumber(null)).toBe("—");
    expect(fmtPct(37.9)).toMatch(/37\.9%/);
    expect(fmtPct(null)).toBe("—");
  });
});

describe("fmtDelta", () => {
  it("signs positive and negative deltas", () => {
    expect(fmtDelta(12.5)).toMatch(/\+12\.5/);
    expect(fmtDelta(-3.2)).toMatch(/−?-3\.2/);
    expect(fmtDelta(null)).toBe("—");
  });
});

describe("titleCase", () => {
  it("humanizes identifiers", () => {
    expect(titleCase("annual_report")).toBe("Annual Report");
  });
});

describe("DOC_TYPE_LABELS", () => {
  it("covers the full document type enum", () => {
    for (const t of ["annual_report", "10_k", "10_q", "earnings_report", "investor_presentation",
                     "financial_statement", "market_report", "press_release", "other"]) {
      expect(DOC_TYPE_LABELS[t]).toBeTruthy();
    }
  });
});
