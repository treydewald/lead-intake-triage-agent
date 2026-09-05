// Static mirror of the backend's `graph.py` STAGE_ORDER (TypeScript can't import a
// Python constant) — a deliberately duplicated 6-item list, not a duplicated system:
// the backend remains the sole source of truth for trace data. If a stage is ever
// added to STAGE_ORDER, this list must be updated too. See
// architecture-plan-feature-08.md.
export interface StageOrderEntry {
  key: string
  label: string
}

export const STAGE_ORDER: StageOrderEntry[] = [
  { key: 'intake_parsing', label: 'Intake Parsing' },
  { key: 'intent_classification', label: 'Intent Classification' },
  { key: 'data_enrichment', label: 'Data Enrichment' },
  { key: 'hubspot_crm_write', label: 'HubSpot CRM Write' },
  { key: 'human_review', label: 'Human Review' },
  { key: 'outcome_notification', label: 'Outcome Notification' },
]
