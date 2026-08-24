import type {
  DashboardData,
  DataQualityReport,
  IncidentAiFinding,
  IncidentAiSummary,
  IncidentSummary,
  IncidentTrend,
  MonthlyEmission,
} from './types'

interface DataResponse<T> {
  data: T
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(path, {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    throw new Error(`request failed with status ${response.status}`)
  }

  return response.json() as Promise<T>
}

export async function getDashboardData(): Promise<DashboardData> {
  // load independent dashboard datasets concurrently
  const [
    emissions,
    incidentSummary,
    incidentTrends,
    dataQuality,
    aiFindings,
    aiSummary,
  ] = await Promise.all([
    fetchJson<DataResponse<MonthlyEmission[]>>('/api/emissions/monthly'),
    fetchJson<IncidentSummary>('/api/incidents/summary'),
    fetchJson<DataResponse<IncidentTrend[]>>('/api/incidents/trends'),
    fetchJson<DataQualityReport>('/api/data-quality'),
    fetchJson<DataResponse<IncidentAiFinding[]>>(
      '/api/incidents/ai-findings',
    ),
    fetchJson<IncidentAiSummary>('/api/incidents/ai-summary'),
  ])

  return {
    emissions: emissions.data,
    incidentSummary,
    incidentTrends: incidentTrends.data,
    dataQuality,
    aiFindings: aiFindings.data,
    aiSummary,
  }
}
