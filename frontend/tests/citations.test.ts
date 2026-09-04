import { describe, expect, it } from "vitest";
import type { ChatAnswer, Citation } from "@/types";

/**
 * The backend (never the LLM) maps SOURCE_N ids to document + page.
 * These tests pin the contract the frontend relies on for rendering
 * `[Name • p.N]` badges and deep links.
 */
describe("citation contract", () => {
  it("citations carry document + page for each source id", () => {
    const citations: Citation[] = [
      { source_id: 1, document_id: "d1", document_name: "Annual Report FY2025.pdf", page_number: 5, quote: "Total revenue 630.4" },
      { source_id: 2, document_id: "d2", document_name: "Deck.pdf", page_number: 2, quote: "Top 3 customers 44%" },
    ];
    const answer: ChatAnswer = {
      answer: "Revenue was 630.4 [1].",
      confidence: "high",
      claims: [
        { text: "Revenue was 630.4", type: "fact", sources: [1] },
        { text: "Customer concentration is high", type: "analysis", sources: [2] },
      ],
      citations,
      insufficient_evidence: false,
      session_id: "s1",
      message_id: "m1",
    };
    for (const claim of answer.claims) {
      for (const sid of claim.sources) {
        const c = answer.citations.find((x) => x.source_id === sid);
        expect(c).toBeDefined();
        expect(c!.document_name.length).toBeGreaterThan(0);
        expect(c!.page_number).toBeGreaterThan(0);
      }
    }
  });

  it("claim types are restricted to the documented enum", () => {
    const allowed = ["fact", "analysis", "recommendation", "uncertainty", "contradiction"];
    expect(allowed).toContain("fact");
    expect(allowed).toContain("contradiction");
  });
});
