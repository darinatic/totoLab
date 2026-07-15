import { watch, onActivated, onDeactivated } from 'vue'
import { storeToRefs } from 'pinia'
import { useUiStore } from '../stores/ui'

// Re-run `reload` when the global lookback window changes, but only while this
// view is the active (visible) one. Kept-alive inactive views reload lazily on
// their next activation if the window changed while they were hidden - so a
// window change never triggers a burst of background refetches (incl. slow ML).
export function useWindowReload(reload) {
  const { window } = storeToRefs(useUiStore())
  let active = true
  let loaded = window.value

  watch(window, (w) => {
    if (active) { loaded = w; reload() }
  })
  onActivated(() => {
    active = true
    if (loaded !== window.value) { loaded = window.value; reload() }
  })
  onDeactivated(() => { active = false })
}
