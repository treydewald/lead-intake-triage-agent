import type { BenchmarkCase } from './api'

export interface ThresholdSimulationResult {
  threshold: number
  totalCases: number
  autoCount: number
  reviewCount: number
  autoCorrect: number
  autoIncorrect: number
  autoAmbiguous: number
}

// Mirrors `_route_after_enrich`'s real production boundary in
// `backend/app/orchestrator/graph.py` exactly: `confidence >= confidence_threshold`
// auto-proceeds. This convention must never drift independently from that function -
// see architecture-plan-feature-17.md's Risks.
export function simulateThreshold(cases: BenchmarkCase[], threshold: number): ThresholdSimulationResult {
  let autoCount = 0
  let autoCorrect = 0
  let autoIncorrect = 0
  let autoAmbiguous = 0

  for (const item of cases) {
    const confidence = item.confidence ?? 0
    const wouldAutoProcess = confidence >= threshold
    if (!wouldAutoProcess) continue

    autoCount += 1
    if (item.is_ambiguous) {
      autoAmbiguous += 1
    } else if (item.correct) {
      autoCorrect += 1
    } else {
      autoIncorrect += 1
    }
  }

  return {
    threshold,
    totalCases: cases.length,
    autoCount,
    reviewCount: cases.length - autoCount,
    autoCorrect,
    autoIncorrect,
    autoAmbiguous,
  }
}
