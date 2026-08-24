<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { getDashboardData } from './api'
import EmissionsChart from './components/EmissionsChart.vue'
import IncidentTrendChart from './components/IncidentTrendChart.vue'
import type {
  DashboardData,
  DataQualityIssue,
  IncidentAiFinding,
} from './types'

const dashboard = ref<DashboardData | null>(null)
const loading = ref(true)
const errorMessage = ref('')
const lastUpdated = ref<Date | null>(null)

// derive decision-ready metrics from the API responses
const totalEmissionsTonnes = computed(() => {
  if (!dashboard.value) {
    return 0
  }

  return (
    dashboard.value.emissions.reduce(
      (total, item) => total + item.totalKgCO2e,
      0,
    ) / 1_000
  )
})

const reportingPeriod = computed(() => {
  const emissions = dashboard.value?.emissions

  if (!emissions?.length) {
    return 'Reporting period unavailable'
  }

  return `${formatMonth(emissions[0].month)}-${formatMonth(
    emissions[emissions.length - 1].month,
  )}`
})

const aiProgress = computed(() => {
  const totalIncidents = dashboard.value?.incidentSummary.totalIncidents ?? 0
  const analyzed = dashboard.value?.aiSummary.totalAnalyzed ?? 0

  if (!totalIncidents) {
    return 0
  }

  return Math.min(100, Math.round((analyzed / totalIncidents) * 100))
})

const highSeverityCount = computed(() =>
  dashboard.value?.incidentSummary.bySeverity.find(
    (item) => item.severity === 'High',
  )?.count ?? 0,
)

// surface findings that need human attention first
const attentionFindings = computed(() => {
  if (!dashboard.value) {
    return []
  }

  return dashboard.value.aiFindings
    .filter(
      (finding) =>
        finding.psychosocialHazard ||
        finding.severityConsistency === 'appears_inconsistent',
    )
    .sort((first, second) => {
      const firstPriority =
        first.severityConsistency === 'appears_inconsistent' ? 0 : 1
      const secondPriority =
        second.severityConsistency === 'appears_inconsistent' ? 0 : 1

      return firstPriority - secondPriority
    })
    .slice(0, 4)
})

const priorityQualityIssues = computed(() => {
  if (!dashboard.value) {
    return []
  }

  return dashboard.value.dataQuality.issues
    .filter((issue) => issue.action !== 'fixed')
    .slice(0, 5)
})

// keep existing data visible while a manual refresh runs
async function loadDashboard(): Promise<void> {
  loading.value = true
  errorMessage.value = ''

  try {
    dashboard.value = await getDashboardData()
    lastUpdated.value = new Date()
  }
  catch (error) {
    console.error(error)
    errorMessage.value =
      'The dashboard could not reach the API. Check that the backend is running on port 3000.'
  }
  finally {
    loading.value = false
  }
}

function formatNumber(value: number, maximumFractionDigits = 0): string {
  return new Intl.NumberFormat('en-AU', {
    maximumFractionDigits,
  }).format(value)
}

function formatMonth(month: string): string {
  const [year, monthNumber] = month.split('-')
  const date = new Date(Number(year), Number(monthNumber) - 1, 1)

  return new Intl.DateTimeFormat('en-AU', {
    month: 'short',
    year: 'numeric',
  }).format(date)
}

function formatTimestamp(date: Date): string {
  return new Intl.DateTimeFormat('en-AU', {
    hour: 'numeric',
    minute: '2-digit',
  }).format(date)
}

function formatLabel(value: string): string {
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function findingStatus(finding: IncidentAiFinding): string {
  if (finding.severityConsistency === 'appears_inconsistent') {
    return 'Severity review'
  }

  return 'Psychosocial'
}

function qualityIssueDescription(issue: DataQualityIssue): string {
  const detail = issue.details.details

  if (typeof detail === 'string') {
    return detail
  }

  if (
    typeof detail === 'object' &&
    detail !== null &&
    'reason' in detail &&
    typeof detail.reason === 'string'
  ) {
    return detail.reason
  }

  return formatLabel(issue.issueType)
}

onMounted(loadDashboard)
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="#overview" aria-label="Ironbark Ridge overview">
        <span class="brand-mark" aria-hidden="true">
          <span></span>
          <span></span>
        </span>
        <span>
          <strong>Ironbark Ridge</strong>
          <small>Compliance intelligence</small>
        </span>
      </a>

      <nav class="topnav" aria-label="dashboard sections">
        <a href="#overview">Overview</a>
        <a href="#operations">Operations</a>
        <a href="#attention">Attention</a>
      </nav>

      <button
        class="refresh-button"
        type="button"
        :disabled="loading"
        @click="loadDashboard"
      >
        <svg viewBox="0 0 20 20" aria-hidden="true">
          <path
            d="M15.4 6.2A6 6 0 1 0 16 12"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-width="1.7"
          />
          <path
            d="M12.7 3.8h3.2v3.3"
            fill="none"
            stroke="currentColor"
            stroke-linecap="round"
            stroke-linejoin="round"
            stroke-width="1.7"
          />
        </svg>
        {{ loading ? 'Refreshing' : 'Refresh data' }}
      </button>
    </header>

    <main>
      <section id="overview" class="page-intro">
        <div>
          <p class="eyebrow">Sustainability command view</p>
          <h1>Operational risk, without the noise</h1>
          <p class="intro-copy">
            Emissions, safety, and data confidence for
            {{ reportingPeriod }} in one decision-ready view
          </p>
        </div>

        <div class="system-status">
          <span class="status-dot" :class="{ muted: errorMessage }"></span>
          <span>
            <strong>{{ errorMessage ? 'API unavailable' : 'Data connected' }}</strong>
            <small v-if="lastUpdated">
              Updated {{ formatTimestamp(lastUpdated) }}
            </small>
            <small v-else>Waiting for first refresh</small>
          </span>
        </div>
      </section>

      <section v-if="loading && !dashboard" class="loading-grid" aria-label="loading dashboard">
        <div v-for="item in 8" :key="item" class="skeleton-card"></div>
      </section>

      <section v-else-if="errorMessage && !dashboard" class="error-state">
        <span class="error-icon">!</span>
        <div>
          <p class="eyebrow">Connection issue</p>
          <h2>We could not load the compliance data</h2>
          <p>{{ errorMessage }}</p>
        </div>
        <button type="button" @click="loadDashboard">Try again</button>
      </section>

      <template v-else-if="dashboard">
        <section class="metric-grid" aria-label="headline compliance metrics">
          <article class="metric-card">
            <div class="metric-heading">
              <span class="metric-icon emissions-icon" aria-hidden="true">Co2</span>
              <span class="metric-state neutral">18 months</span>
            </div>
            <p>Total emissions</p>
            <strong>{{ formatNumber(totalEmissionsTonnes) }}</strong>
            <small>tonnes CO2e across Scope 1 and 2</small>
          </article>

          <article class="metric-card">
            <div class="metric-heading">
              <span class="metric-icon incidents-icon" aria-hidden="true">+</span>
              <span class="metric-state warning">
                {{ highSeverityCount }} high severity
              </span>
            </div>
            <p>Recorded incidents</p>
            <strong>{{ dashboard.incidentSummary.totalIncidents }}</strong>
            <small>cleaned records in the incident register</small>
          </article>

          <article class="metric-card">
            <div class="metric-heading">
              <span class="metric-icon quality-icon" aria-hidden="true">-</span>
              <span class="metric-state warning">
                {{ dashboard.dataQuality.summary.byAction.flagged }} open
              </span>
            </div>
            <p>Data-quality issues</p>
            <strong>{{ dashboard.dataQuality.summary.totalIssues }}</strong>
            <small>
              {{ dashboard.dataQuality.summary.byAction.fixed }} corrected at ingestion
            </small>
          </article>

          <article class="metric-card accent-card">
            <div class="metric-heading">
              <span class="metric-icon ai-icon" aria-hidden="true">AI</span>
              <span class="metric-state inverse">{{ aiProgress }}% complete</span>
            </div>
            <p>AI incident review</p>
            <strong>
              {{ dashboard.aiSummary.totalAnalyzed }}
              <span>/ {{ dashboard.incidentSummary.totalIncidents }}</span>
            </strong>
            <div class="progress-track" aria-label="AI analysis progress">
              <span :style="{ width: `${aiProgress}%` }"></span>
            </div>
          </article>
        </section>

        <section id="operations" class="dashboard-grid">
          <article class="panel emissions-panel">
            <header class="panel-header">
              <div>
                <p class="eyebrow">Climate performance</p>
                <h2>Monthly emissions by scope</h2>
              </div>
              <span class="panel-note">kg converted to tonnes</span>
            </header>
            <EmissionsChart :data="dashboard.emissions" />
          </article>

          <article class="panel risk-panel">
            <header class="panel-header">
              <div>
                <p class="eyebrow">AI review signals</p>
                <h2>Items requiring judgment</h2>
              </div>
            </header>

            <div class="risk-score">
              <strong>
                {{
                  dashboard.aiSummary.psychosocialHazards +
                  dashboard.aiSummary.severityInconsistencies
                }}
              </strong>
              <span>priority findings</span>
            </div>

            <dl class="risk-breakdown">
              <div>
                <dt>Psychosocial hazards</dt>
                <dd>{{ dashboard.aiSummary.psychosocialHazards }}</dd>
              </div>
              <div>
                <dt>Severity inconsistencies</dt>
                <dd>{{ dashboard.aiSummary.severityInconsistencies }}</dd>
              </div>
              <div>
                <dt>Insufficient context</dt>
                <dd>{{ dashboard.aiSummary.insufficientContext }}</dd>
              </div>
            </dl>

            <p class="risk-footnote">
              AI findings are screening signals, not final compliance decisions
            </p>
          </article>

          <article class="panel incidents-panel">
            <header class="panel-header">
              <div>
                <p class="eyebrow">Safety performance</p>
                <h2>Incident volume and severity</h2>
              </div>
              <span class="panel-note">
                {{ dashboard.incidentSummary.totalIncidents }} total incidents
              </span>
            </header>
            <IncidentTrendChart :data="dashboard.incidentTrends" />
          </article>
        </section>

        <section id="attention" class="attention-grid">
          <article class="panel attention-panel">
            <header class="panel-header">
              <div>
                <p class="eyebrow">Grounded AI review</p>
                <h2>Attention queue</h2>
              </div>
              <span class="panel-note">evidence retained from source records</span>
            </header>

            <div v-if="attentionFindings.length" class="finding-list">
              <article
                v-for="finding in attentionFindings"
                :key="finding.recordHash"
                class="finding-item"
              >
                <div class="finding-meta">
                  <span
                    class="finding-badge"
                    :class="{
                      critical:
                        finding.severityConsistency === 'appears_inconsistent',
                    }"
                  >
                    {{ findingStatus(finding) }}
                  </span>
                  <span>{{ finding.incidentId }}</span>
                  <span>{{ finding.location }}</span>
                </div>
                <h3>
                  {{ formatLabel(finding.primaryHazardDomain) }}
                  <template v-if="finding.psychosocialTypes.length">
                    &middot; {{ finding.psychosocialTypes.map(formatLabel).join(', ') }}
                  </template>
                </h3>
                <blockquote>&ldquo;{{ finding.categoryEvidenceQuote }}&rdquo;</blockquote>
                <div class="finding-footer">
                  <span>
                    Recorded {{ finding.recordedSeverity }}
                    <template
                      v-if="
                        finding.severityConsistency === 'appears_inconsistent'
                      "
                    >
                     !&rarr; suggested {{ finding.suggestedSeverity }}
                    </template>
                  </span>
                  <span>Source row {{ finding.sourceRow }}</span>
                </div>
              </article>
            </div>

            <div v-else class="empty-state">
              No psychosocial or severity-inconsistent findings are currently loaded
            </div>
          </article>

          <article class="panel quality-panel">
            <header class="panel-header">
              <div>
                <p class="eyebrow">Data confidence</p>
                <h2>Open quality flags</h2>
              </div>
              <span class="count-badge">
                {{ dashboard.dataQuality.summary.byAction.flagged }}
              </span>
            </header>

            <div class="quality-list">
              <article
                v-for="issue in priorityQualityIssues"
                :key="issue.id"
                class="quality-item"
              >
                <span class="quality-marker"></span>
                <div>
                  <div class="quality-meta">
                    <span>{{ formatLabel(issue.dataset) }}</span>
                    <span v-if="issue.recordKey">{{ issue.recordKey }}</span>
                  </div>
                  <h3>{{ formatLabel(issue.issueType) }}</h3>
                  <p>{{ qualityIssueDescription(issue) }}</p>
                </div>
              </article>
            </div>
          </article>
        </section>
      </template>
    </main>

    <footer>
      <span>Ironbark Ridge Resources</span>
      <span>Grounded intelligence &middot; source evidence preserved</span>
    </footer>
  </div>
</template>
