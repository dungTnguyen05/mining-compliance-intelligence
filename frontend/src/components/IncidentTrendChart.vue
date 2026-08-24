<script setup lang="ts">
import { computed } from 'vue'

import type { IncidentTrend } from '../types'

const props = defineProps<{
  data: IncidentTrend[]
}>()

// use one coordinate system so the SVG scales responsively
const width = 760
const height = 250
const plotLeft = 34
const plotRight = 16
const plotTop = 18
const plotBottom = 44
const plotHeight = height - plotTop - plotBottom
const plotWidth = width - plotLeft - plotRight
const severityOrder = ['Low', 'Medium', 'High'] as const

const maxTotal = computed(() =>
  Math.max(...props.data.map((item) => item.totalIncidents), 1),
)

const groupWidth = computed(() =>
  props.data.length ? plotWidth / props.data.length : plotWidth,
)

const barWidth = computed(() =>
  Math.min(22, Math.max(8, groupWidth.value * 0.58)),
)

function severityCount(
  trend: IncidentTrend,
  severity: (typeof severityOrder)[number],
): number {
  return trend.bySeverity.find((item) => item.severity === severity)?.count ?? 0
}

function segmentHeight(count: number): number {
  return (count / maxTotal.value) * plotHeight
}

// stack each severity above the previous segment
function segmentY(
  trend: IncidentTrend,
  severity: (typeof severityOrder)[number],
): number {
  const severityIndex = severityOrder.indexOf(severity)
  const cumulativeCount = severityOrder
    .slice(0, severityIndex + 1)
    .reduce((total, item) => total + severityCount(trend, item), 0)

  return plotTop + plotHeight - segmentHeight(cumulativeCount)
}

function xPosition(index: number): number {
  return (
    plotLeft +
    groupWidth.value * (index + 0.5) -
    barWidth.value / 2
  )
}

function formatMonth(month: string): string {
  const [year, monthNumber] = month.split('-')
  const labels = [
    'Jan',
    'Feb',
    'Mar',
    'Apr',
    'May',
    'Jun',
    'Jul',
    'Aug',
    'Sep',
    'Oct',
    'Nov',
    'Dec',
  ]

  return `${labels[Number(monthNumber) - 1]} ${year.slice(2)}`
}
</script>

<template>
  <div class="chart-wrap">
    <svg
      class="chart"
      :viewBox="`0 0 ${width} ${height}`"
      role="img"
      aria-label="monthly incidents grouped by severity"
    >
      <line
        :x1="plotLeft"
        :x2="width - plotRight"
        :y1="plotTop + plotHeight"
        :y2="plotTop + plotHeight"
        class="grid-line baseline"
      />

      <g v-for="(trend, index) in data" :key="trend.month">
        <rect
          v-for="severity in severityOrder"
          :key="severity"
          :x="xPosition(index)"
          :y="segmentY(trend, severity)"
          :width="barWidth"
          :height="segmentHeight(severityCount(trend, severity))"
          :class="`incident-bar severity-${severity.toLowerCase()}`"
        >
          <title>
            {{ formatMonth(trend.month) }} {{ severity }}:
            {{ severityCount(trend, severity) }}
          </title>
        </rect>
        <text
          :x="xPosition(index) + barWidth / 2"
          :y="segmentY(trend, 'High') - 7"
          class="bar-total"
        >
          {{ trend.totalIncidents }}
        </text>
        <text
          v-if="index % 3 === 0 || index === data.length - 1"
          :x="xPosition(index) + barWidth / 2"
          :y="height - 16"
          class="axis-label axis-label-x"
        >
          {{ formatMonth(trend.month) }}
        </text>
      </g>
    </svg>

    <div class="chart-legend" aria-label="incident chart legend">
      <span><i class="legend-swatch severity-low"></i>Low</span>
      <span><i class="legend-swatch severity-medium"></i>Medium</span>
      <span><i class="legend-swatch severity-high"></i>High</span>
    </div>
  </div>
</template>
