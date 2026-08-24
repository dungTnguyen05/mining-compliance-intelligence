export interface MonthlyEmission {
  month: string
  scope1KgCO2e: number
  scope2KgCO2e: number
  totalKgCO2e: number
}

export interface IncidentTypeCount {
  typeCode: string
  count: number
}

export interface IncidentSeverityCount {
  severity: string
  count: number
}

export interface IncidentSummary {
  totalIncidents: number
  byType: IncidentTypeCount[]
  bySeverity: IncidentSeverityCount[]
}

export interface IncidentTrend {
  month: string
  totalIncidents: number
  byType: IncidentTypeCount[]
  bySeverity: IncidentSeverityCount[]
}

export type DataQualityAction = 'fixed' | 'flagged' | 'rejected'

export interface DataQualityIssue {
  id: number
  dataset: string
  issueType: string
  action: DataQualityAction
  recordKey: string | null
  details: Record<string, unknown>
  createdAt: string
}

export interface DataQualityReport {
  summary: {
    totalIssues: number
    byAction: Record<DataQualityAction, number>
    byDataset: Record<string, number>
  }
  issues: DataQualityIssue[]
}

export interface IncidentAiFinding {
  incidentId: string
  incidentDate: string
  location: string
  recordedTypeCode: string
  recordedSeverity: string
  description: string
  sourceRow: number
  recordHash: string
  primaryHazardDomain: string
  secondaryHazardDomains: string[]
  eventMechanism: string
  psychosocialHazard: boolean
  psychosocialTypes: string[]
  severityConsistency:
    | 'consistent'
    | 'appears_inconsistent'
    | 'insufficient_context'
  suggestedSeverity: string
  categoryEvidenceQuote: string
  severityEvidenceQuote: string | null
  explanation: string
  responseId: string | null
  model: string
  processedAt: string
  attempts: number
}

export interface IncidentAiSummary {
  totalAnalyzed: number
  psychosocialHazards: number
  severityInconsistencies: number
  insufficientContext: number
}

export interface DashboardData {
  emissions: MonthlyEmission[]
  incidentSummary: IncidentSummary
  incidentTrends: IncidentTrend[]
  dataQuality: DataQualityReport
  aiFindings: IncidentAiFinding[]
  aiSummary: IncidentAiSummary
}
