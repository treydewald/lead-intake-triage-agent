import { describe, expect, it } from 'vitest'
import { simulateThreshold } from './thresholdSimulation'
import type { BenchmarkCase } from './api'

function makeCase(overrides: Partial<BenchmarkCase>): BenchmarkCase {
  return {
    case_id: 'case-1',
    category: 'buyer',
    expected_label: 'buyer',
    is_ambiguous: false,
    predicted_label: 'buyer',
    confidence: 0.9,
    correct: true,
    consistent: true,
    ...overrides,
  }
}

describe('simulateThreshold', () => {
  it('sends every case to auto-processing at threshold 0.0', () => {
    const cases = [makeCase({ confidence: 0.1 }), makeCase({ confidence: 0.9 })]

    const result = simulateThreshold(cases, 0.0)

    expect(result.autoCount).toBe(2)
    expect(result.reviewCount).toBe(0)
  })

  it('sends every case to review at threshold 1.0 unless confidence is exactly 1.0', () => {
    const cases = [makeCase({ confidence: 0.99 }), makeCase({ confidence: 1.0 })]

    const result = simulateThreshold(cases, 1.0)

    expect(result.autoCount).toBe(1)
    expect(result.reviewCount).toBe(1)
  })

  it('treats confidence exactly equal to the threshold as auto-processed (>= boundary)', () => {
    const cases = [makeCase({ confidence: 0.7 })]

    const result = simulateThreshold(cases, 0.7)

    expect(result.autoCount).toBe(1)
    expect(result.reviewCount).toBe(0)
  })

  it('splits auto-processed cases into correct/incorrect/ambiguous', () => {
    const cases = [
      makeCase({ case_id: 'a', confidence: 0.9, correct: true, is_ambiguous: false }),
      makeCase({ case_id: 'b', confidence: 0.9, correct: false, is_ambiguous: false }),
      makeCase({ case_id: 'c', confidence: 0.9, correct: null, is_ambiguous: true }),
      makeCase({ case_id: 'd', confidence: 0.1, correct: true, is_ambiguous: false }),
    ]

    const result = simulateThreshold(cases, 0.7)

    expect(result.autoCount).toBe(3)
    expect(result.reviewCount).toBe(1)
    expect(result.autoCorrect).toBe(1)
    expect(result.autoIncorrect).toBe(1)
    expect(result.autoAmbiguous).toBe(1)
  })

  it('never counts an ambiguous case as correct or incorrect', () => {
    const cases = [makeCase({ confidence: 0.9, correct: null, is_ambiguous: true })]

    const result = simulateThreshold(cases, 0.5)

    expect(result.autoCorrect).toBe(0)
    expect(result.autoIncorrect).toBe(0)
    expect(result.autoAmbiguous).toBe(1)
  })

  it('reports zero misclassified and zero ambiguous counts for a clean run', () => {
    const cases = [makeCase({ confidence: 0.95, correct: true, is_ambiguous: false })]

    const result = simulateThreshold(cases, 0.7)

    expect(result.autoIncorrect).toBe(0)
    expect(result.autoAmbiguous).toBe(0)
  })

  it('handles an empty case list', () => {
    const result = simulateThreshold([], 0.7)

    expect(result.totalCases).toBe(0)
    expect(result.autoCount).toBe(0)
    expect(result.reviewCount).toBe(0)
  })
})
