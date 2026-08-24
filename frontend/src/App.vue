<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

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

const SECTION_IDS = [
  'site-overview',
  'performance',
  'review-queue',
] as const
type SectionId = typeof SECTION_IDS[number]
const LEGACY_SECTION_IDS: Record<string, SectionId> = {
  '#overview': 'site-overview',
  '#operations': 'performance',
  '#attention': 'review-queue',
}

const activeSection = ref<SectionId>('site-overview')
let scrollFrame: number | null = null

// derive decision-ready metrics from the API responses
const totalEmissionsTonnes = computed(() => {
  if (!dashboard.value) {
    return 0
  }

  return (
    dashboard.value.emissions.reduce(
      (total, item) =>
        total + (item.scope1KgCO2e ?? 0) + (item.scope2KgCO2e ?? 0),
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

const incompleteEmissionsMonths = computed(() =>
  dashboard.value?.emissions
    .filter((item) => item.missingScopes.length > 0)
    .map((item) => item.month) ?? [],
)

const powerDisruptionInsight = computed(() => {
  if (!dashboard.value) {
    return null
  }

  const february = dashboard.value.emissions.find(
    (item) => item.month === '2026-02',
  )
  const march = dashboard.value.emissions.find(
    (item) => item.month === '2026-03',
  )
  const outageFinding = dashboard.value.aiFindings.find(
    (finding) => finding.incidentId === 'INC-2026-131',
  )
  const fatigueFinding = dashboard.value.aiFindings.find(
    (finding) => finding.incidentId === 'INC-2026-134',
  )

  if (
    february?.scope1KgCO2e == null ||
    february.scope2KgCO2e == null ||
    march?.scope1KgCO2e == null ||
    march.scope2KgCO2e == null ||
    !outageFinding ||
    !fatigueFinding
  ) {
    return null
  }

  return {
    scope1Increase: Math.round(
      ((march.scope1KgCO2e - february.scope1KgCO2e) /
        february.scope1KgCO2e) *
        100,
    ),
    scope2Decrease: Math.round(
      ((february.scope2KgCO2e - march.scope2KgCO2e) /
        february.scope2KgCO2e) *
        100,
    ),
    outageIncidentId: outageFinding.incidentId,
    fatigueIncidentId: fatigueFinding.incidentId,
  }
})

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

const ACRONYM_LABELS: Record<string, string> = {
  abn: 'ABN',
  ai: 'AI',
  api: 'API',
  co2e: 'CO2e',
  id: 'ID',
  ivms: 'IVMS',
  lti: 'LTI',
  lv: 'LV',
  rpe: 'RPE',
}

function formatLabel(value: string): string {
  return value
    .replaceAll('_', ' ')
    .split(' ')
    .map((word) => {
      const normalizedWord = word.toLowerCase()

      return (
        ACRONYM_LABELS[normalizedWord] ??
        `${normalizedWord.charAt(0).toUpperCase()}${normalizedWord.slice(1)}`
      )
    })
    .join(' ')
}

function formatAcronyms(value: string): string {
  return value.replace(/\b(abn|ai|api|id|ivms|lti|lv|rpe)\b/gi, (word) =>
    ACRONYM_LABELS[word.toLowerCase()] ?? word,
  )
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
    return formatAcronyms(detail)
  }

  if (
    typeof detail === 'object' &&
    detail !== null &&
    'reason' in detail &&
    typeof detail.reason === 'string'
  ) {
    return formatAcronyms(detail.reason)
  }

  return formatLabel(issue.issueType)
}

function updateActiveSection(): void {
  const sections = SECTION_IDS
    .map((sectionId) => document.getElementById(sectionId))
    .filter((section): section is HTMLElement => section !== null)

  if (!sections.length) {
    return
  }

  if (
    window.innerHeight + window.scrollY >=
    document.documentElement.scrollHeight - 2
  ) {
    activeSection.value = SECTION_IDS[SECTION_IDS.length - 1]
    return
  }

  const headerOffset = 112
  let currentSection = sections[0].id as SectionId

  for (const section of sections) {
    if (section.getBoundingClientRect().top <= headerOffset) {
      currentSection = section.id as SectionId
    }
  }

  activeSection.value = currentSection
}

function scheduleNavigationUpdate(): void {
  if (scrollFrame !== null) {
    return
  }

  scrollFrame = window.requestAnimationFrame(() => {
    scrollFrame = null
    updateActiveSection()
  })
}

onMounted(() => {
  const replacementSection = LEGACY_SECTION_IDS[window.location.hash]

  if (replacementSection) {
    window.history.replaceState(null, '', `#${replacementSection}`)
  }

  void loadDashboard().finally(() => {
    window.requestAnimationFrame(() => {
      const hash = window.location.hash
      const target = hash
        ? document.querySelector<HTMLElement>(hash)
        : null

      target?.scrollIntoView()
      updateActiveSection()
    })
  })

  window.addEventListener('scroll', scheduleNavigationUpdate, {
    passive: true,
  })
  window.addEventListener('resize', scheduleNavigationUpdate)
  scheduleNavigationUpdate()
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', scheduleNavigationUpdate)
  window.removeEventListener('resize', scheduleNavigationUpdate)

  if (scrollFrame !== null) {
    window.cancelAnimationFrame(scrollFrame)
  }
})
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="#site-overview" aria-label="Ironbark Ridge site overview">
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
        <a
          href="#site-overview"
          :class="{ active: activeSection === 'site-overview' }"
          :aria-current="activeSection === 'site-overview' ? 'location' : undefined"
        >
          Site overview
        </a>
        <a
          href="#performance"
          :class="{ active: activeSection === 'performance' }"
          :aria-current="activeSection === 'performance' ? 'location' : undefined"
        >
          Performance
        </a>
        <a
          href="#review-queue"
          :class="{ active: activeSection === 'review-queue' }"
          :aria-current="activeSection === 'review-queue' ? 'location' : undefined"
        >
          Review queue
        </a>
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
      <section id="site-overview" class="page-intro" data-nav-section>
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
            <p>Reported emissions</p>
            <strong>{{ formatNumber(totalEmissionsTonnes) }}</strong>
            <small>tonnes CO2e from available Scope 1 and 2 data</small>
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

        <section id="performance" class="dashboard-grid" data-nav-section>
          <article class="panel emissions-panel">
            <header class="panel-header">
              <div>
                <p class="eyebrow">Climate performance</p>
                <h2>Monthly emissions by scope</h2>
              </div>
              <div class="panel-notes">
                <span
                  v-if="incompleteEmissionsMonths.length"
                  class="completeness-note"
                  :title="incompleteEmissionsMonths.map(formatMonth).join(', ')"
                >
                  {{ incompleteEmissionsMonths.length }} incomplete month{{ incompleteEmissionsMonths.length === 1 ? '' : 's' }}
                </span>
                <span class="panel-note">kg converted to tonnes</span>
              </div>
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

          <article
            v-if="powerDisruptionInsight"
            class="panel linked-insight-panel"
          >
            <div class="linked-insight-copy">
              <p class="eyebrow">Cross-dataset signal</p>
              <h2>March outage shifted the emissions profile</h2>
              <p>
                Scope 1 rose while Scope 2 fell as the site moved from grid
                electricity to backup diesel generation. The same disruption
                period also contains a workforce fatigue signal.
              </p>
              <div class="insight-evidence" aria-label="supporting source records">
                <span>
                  Grid disruption
                  <strong>{{ powerDisruptionInsight.outageIncidentId }}</strong>
                </span>
                <span>
                  Crew fatigue
                  <strong>{{ powerDisruptionInsight.fatigueIncidentId }}</strong>
                </span>
              </div>
              <small>
                cross-dataset correlation for review, not proof of causation
              </small>
            </div>

            <div class="insight-shifts" aria-label="February to March 2026 change">
              <div>
                <span>Scope 1</span>
                <strong>+{{ powerDisruptionInsight.scope1Increase }}%</strong>
                <small>vs Feb 2026</small>
              </div>
              <div>
                <span>Scope 2</span>
                <strong>-{{ powerDisruptionInsight.scope2Decrease }}%</strong>
                <small>vs Feb 2026</small>
              </div>
            </div>
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

        <section id="review-queue" class="attention-grid" data-nav-section>
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
