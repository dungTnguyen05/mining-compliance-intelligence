<script setup lang="ts">
import { computed, ref } from 'vue'

import type { MonthlyEmission } from '../types'

const props = defineProps<{
  data: MonthlyEmission[]
}>()

const activeIndex = ref<number | null>(null)

const activeItem = computed(() => {
  if (activeIndex.value === null) {
    return null
  }

  return props.data[activeIndex.value] ?? null
})

const tooltipX = computed(() => {
  if (activeIndex.value === null) {
    return 0
  }

  const center = xPosition(activeIndex.value, 0)

  return Math.min(Math.max(center - 95, 4), width - 194)
})

// use one coordinate system so the SVG scales responsively
const width = 760
const height = 278
const plotLeft = 54
const plotRight = 18
const plotTop = 20
const plotBottom = 46
const plotHeight = height - plotTop - plotBottom
const plotWidth = width - plotLeft - plotRight

const maxValue = computed(() => {
  const largestValue = Math.max(
    ...props.data.flatMap((item) => [
      item.scope1KgCO2e,
      item.scope2KgCO2e,
    ]),
    1,
  )

  return Math.ceil(largestValue / 500_000) * 500_000
})

const ticks = computed(() =>
  Array.from({ length: 5 }, (_, index) => {
    const value = (maxValue.value / 4) * index

    return {
      value,
      y: plotTop + plotHeight - (value / maxValue.value) * plotHeight,
    }
  }),
)

const groupWidth = computed(() =>
  props.data.length ? plotWidth / props.data.length : plotWidth,
)

const barWidth = computed(() =>
  Math.min(12, Math.max(5, groupWidth.value * 0.28)),
)

function xPosition(index: number, offset: number): number {
  const groupCenter = plotLeft + groupWidth.value * (index + 0.5)

  return groupCenter + offset
}

function barHeight(value: number): number {
  return (value / maxValue.value) * plotHeight
}

function formatAxisValue(value: number): string {
  return `${(value / 1_000_000).toFixed(value ? 1 : 0)}m`
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

function formatTonnes(value: number): string {
  return new Intl.NumberFormat('en-AU', {
    maximumFractionDigits: 0,
  }).format(value / 1_000)
}
function showTooltip(index: number): void {
  activeIndex.value = index
}

function hideTooltip(): void {
  activeIndex.value = null
}

function emissionAriaLabel(item: MonthlyEmission): string {
  return `${formatMonth(item.month)}, Scope 1 ${formatTonnes(item.scope1KgCO2e)} tonnes CO2e, Scope 2 ${formatTonnes(item.scope2KgCO2e)} tonnes CO2e, total ${formatTonnes(item.totalKgCO2e)} tonnes CO2e`
}

</script>

<template>
  <div class="chart-wrap interactive-chart">
    <svg
      class="chart"
      :viewBox="`0 0 ${width} ${height}`"
      role="img"
      aria-label="monthly scope 1 and scope 2 emissions"
    >
      <g v-for="tick in ticks" :key="tick.value">
        <line
          :x1="plotLeft"
          :x2="width - plotRight"
          :y1="tick.y"
          :y2="tick.y"
          class="grid-line"
        />
        <text
          :x="plotLeft - 10"
          :y="tick.y + 4"
          class="axis-label axis-label-y"
        >
          {{ formatAxisValue(tick.value) }}
        </text>
      </g>

      <g
        v-for="(item, index) in data"
        :key="item.month"
        class="chart-group"
        :class="{ active: activeIndex === index }"
        tabindex="0"
        role="img"
        :aria-label="emissionAriaLabel(item)"
        @mouseenter="showTooltip(index)"
        @mouseleave="hideTooltip"
        @focus="showTooltip(index)"
        @blur="hideTooltip"
        @click="showTooltip(index)"
      >
        <rect
          :x="xPosition(index, -barWidth - 1)"
          :y="plotTop + plotHeight - barHeight(item.scope1KgCO2e)"
          :width="barWidth"
          :height="barHeight(item.scope1KgCO2e)"
          rx="3"
          class="bar bar-scope-1"
        >
        </rect>
        <rect
          :x="xPosition(index, 1)"
          :y="plotTop + plotHeight - barHeight(item.scope2KgCO2e)"
          :width="barWidth"
          :height="barHeight(item.scope2KgCO2e)"
          rx="3"
          class="bar bar-scope-2"
        >
        </rect>
        <text
          v-if="index % 3 === 0 || index === data.length - 1"
          :x="xPosition(index, 0)"
          :y="height - 18"
          class="axis-label axis-label-x"
        >
          {{ formatMonth(item.month) }}
        </text>
      </g>
      <g
        v-if="activeItem"
        :transform="`translate(${tooltipX}, 8)`"
        class="svg-tooltip"
        role="tooltip"
      >
        <rect class="svg-tooltip-background" width="190" height="78" rx="9" />
        <text x="12" y="19" class="svg-tooltip-title">
          {{ formatMonth(activeItem.month) }}
        </text>
        <text x="12" y="38" class="svg-tooltip-label">Scope 1</text>
        <text x="178" y="38" class="svg-tooltip-value">
          {{ formatTonnes(activeItem.scope1KgCO2e) }} t CO2e
        </text>
        <text x="12" y="54" class="svg-tooltip-label">Scope 2</text>
        <text x="178" y="54" class="svg-tooltip-value">
          {{ formatTonnes(activeItem.scope2KgCO2e) }} t CO2e
        </text>
        <text x="12" y="70" class="svg-tooltip-label">Total</text>
        <text x="178" y="70" class="svg-tooltip-value total">
          {{ formatTonnes(activeItem.totalKgCO2e) }} t CO2e
        </text>
      </g>

    </svg>

    <div class="chart-legend" aria-label="emissions chart legend">
      <span><i class="legend-swatch scope-1"></i>Scope 1</span>
      <span><i class="legend-swatch scope-2"></i>Scope 2</span>
      <span class="legend-unit">tonnes CO2e</span>
    </div>
  </div>
</template>
