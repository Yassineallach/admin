package com.airpointer.remote.ads

/**
 * Per-placement native ad cache (pure logic, unit-tested; [AdsManager] supplies the real SDK).
 *
 *  • one ad per placement, reused when the user returns to that screen (no reload per visit);
 *  • refreshed only on a later visit once it is [refreshAfterMs] old — never while it is shown;
 *  • served native ads expire after about an hour, so an ad older than [maxAgeMs] is never shown;
 *  • duplicate requests are ignored while one is in flight;
 *  • after a failure, no new request for [failureBackoffMs] (no aggressive retrying);
 *  • every ad that is replaced or evicted is passed to [destroy] (frees the SDK's resources).
 *
 * Not thread-safe: use from the main thread.
 */
class NativeAdCache<P, T>(
    private val clock: () -> Long,
    private val destroy: (T) -> Unit,
    val refreshAfterMs: Long = 30 * 60_000L,
    val maxAgeMs: Long = 55 * 60_000L,
    val failureBackoffMs: Long = 2 * 60_000L,
) {
    sealed interface Slot<out T> {
        data object Empty : Slot<Nothing>
        data object Loading : Slot<Nothing>
        data class Ready<T>(val ad: T, val loadedAt: Long) : Slot<T>
        data class Failed(val at: Long, val code: Int) : Slot<Nothing>
    }

    private val slots = linkedMapOf<P, Slot<T>>()
    private val inFlight = mutableSetOf<P>()

    fun slot(p: P): Slot<T> = slots[p] ?: Slot.Empty

    /** The ad to display for [p] right now, or null (expired ads are evicted here). */
    fun displayable(p: P): T? {
        val s = slots[p] as? Slot.Ready ?: return null
        if (clock() - s.loadedAt >= maxAgeMs) {
            destroy(s.ad)
            slots[p] = Slot.Empty
            return null
        }
        return s.ad
    }

    /** Should a screen showing [p] trigger a request now? */
    fun shouldLoad(p: P): Boolean {
        if (p in inFlight) return false
        return when (val s = slot(p)) {
            Slot.Empty -> true
            Slot.Loading -> false
            is Slot.Ready -> clock() - s.loadedAt >= refreshAfterMs
            is Slot.Failed -> clock() - s.at >= failureBackoffMs
        }
    }

    fun markLoading(p: P) {
        inFlight += p
        // Keep showing a still-valid ad while its replacement loads.
        if (slot(p) !is Slot.Ready) slots[p] = Slot.Loading
    }

    fun onLoaded(p: P, ad: T) {
        inFlight -= p
        (slots[p] as? Slot.Ready)?.let { if (it.ad !== ad) destroy(it.ad) }
        slots[p] = Slot.Ready(ad, clock())
    }

    fun onFailed(p: P, code: Int) {
        inFlight -= p
        val current = slots[p]
        // A failed refresh keeps the previous ad while it is still valid.
        if (current is Slot.Ready && clock() - current.loadedAt < maxAgeMs) return
        if (current is Slot.Ready) destroy(current.ad)
        slots[p] = Slot.Failed(clock(), code)
    }

    /** Destroy everything (consent withdrawn, app shutting down). */
    fun clear() {
        for (s in slots.values) if (s is Slot.Ready) destroy(s.ad)
        slots.clear(); inFlight.clear()
    }
}
