/**
 * Whether a chapter-progress step string refers to the page at `segIndex`
 * (0-based position in the chapter's full segment list — build_scenes numbers
 * pages over the unfiltered list, so position+1 IS the page number).
 *
 * Case-insensitive on purpose: the pipeline writes "Illustrating page 3/38..."
 * but the backend's file-count fallback writes "Page 3/38", and a
 * case-sensitive match silently dropped the amber highlight on that path.
 * The trailing "/" keeps "page 1/" from matching "page 11/".
 */
export function isSegmentPageStep(currentStep: string | null | undefined, segIndex: number): boolean {
  if (!currentStep) return false;
  return currentStep.toLowerCase().includes(`page ${segIndex + 1}/`);
}
