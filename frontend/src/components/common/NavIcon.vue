<script setup lang="ts">
/** 侧边栏导航图标（内联 SVG，避免额外图标库依赖）。 */
const props = defineProps<{ name: string }>()

const PATHS: Record<string, string> = {
  grid: 'M3.5 3.5h7v7h-7zM13.5 3.5h7v7h-7zM3.5 13.5h7v7h-7zM13.5 13.5h7v7h-7z',
  pulse: 'M2.5 12h4l2.5 6.5 5-13 2.5 6.5h5',
  map: 'M3 6.5l6-3 6 3 6-3v14l-6 3-6-3-6 3zM9 3.5v14M15 6.5v14',
  chart: 'M4 4v16h16M8 16.5V10M12.5 16.5V6M17 16.5v-5',
  bars: 'M4 20V11M9.5 20V5M15 20v-6.5M20.5 20V8',
  alert: 'M12 3.5l9 16H3zM12 9.5v4.5M12 17.2h.01',
  database: 'M12 3.5c4.3 0 7.5 1.2 7.5 2.8S16.3 9 12 9 4.5 7.9 4.5 6.3 7.7 3.5 12 3.5zM4.5 6.3v11.4c0 1.6 3.2 2.8 7.5 2.8s7.5-1.2 7.5-2.8V6.3',
  refresh: 'M20 11a8 8 0 1 0-1.7 5.6M20 5v6h-6',
  play: 'M7 4.5l12 7.5-12 7.5z',
  download: 'M12 3.5v11M7.5 10.5l4.5 4.5 4.5-4.5M4 20h16',
  check: 'M4.5 12.5l5 5 10-11',
  menu: 'M4 7h16M4 12h16M4 17h16',
  close: 'M6 6l12 12M18 6L6 18',
  focus: 'M12 4.5v3M12 16.5v3M4.5 12h3M16.5 12h3M8.5 8.5h7v7h-7z',
  present: 'M3.5 5.5h17v11h-17zM9.5 20h5M12 16.5V20',
  info: 'M12 3.5a8.5 8.5 0 1 0 0 17 8.5 8.5 0 0 0 0-17zM12 10.5v6M12 7.6h.01',
}
</script>

<template>
  <svg
    class="nav-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="PATHS[props.name] ?? PATHS.grid" />
  </svg>
</template>

<style scoped>
.nav-icon {
  width: 18px;
  height: 18px;
  flex: 0 0 auto;
}
</style>
