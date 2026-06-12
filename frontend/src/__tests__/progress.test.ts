import { describe, expect, it } from "vitest";
import { isSegmentPageStep } from "@/lib/progress";

describe("isSegmentPageStep", () => {
  it("matches the pipeline's lowercase step strings", () => {
    expect(isSegmentPageStep("Illustrating page 3/38...", 2)).toBe(true);
    expect(isSegmentPageStep("QA checking page 3/38...", 2)).toBe(true);
    expect(isSegmentPageStep("Self-correcting page 3/38...", 2)).toBe(true);
  });

  it("matches the backend fallback's capitalized 'Page N/M'", () => {
    // generation.py's file-count fallback writes "Page 3/38" — the old
    // case-sensitive includes() silently dropped the highlight there.
    expect(isSegmentPageStep("Page 3/38", 2)).toBe(true);
  });

  it("does not cross-match page numbers sharing a prefix", () => {
    expect(isSegmentPageStep("Illustrating page 11/38...", 0)).toBe(false); // page 1 vs 11
    expect(isSegmentPageStep("Illustrating page 1/38...", 10)).toBe(false); // page 11 vs 1
  });

  it("is false for missing or unrelated steps", () => {
    expect(isSegmentPageStep(undefined, 0)).toBe(false);
    expect(isSegmentPageStep(null, 0)).toBe(false);
    expect(isSegmentPageStep("Generating special pages...", 0)).toBe(false);
  });
});
