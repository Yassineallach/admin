package com.airpointer.remote.ads

import com.airpointer.remote.ui.Route
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class NativeAdCacheTest {
    private class Ad(val id: Int) { var destroyed = false }
    private var now = 0L
    private val min = 60_000L
    private fun cache() = NativeAdCache<AdPlacement, Ad>({ now }, { it.destroyed = true })

    @Test fun firstVisitLoadsAndReturnVisitReuses() {
        val c = cache()
        assertTrue(c.shouldLoad(AdPlacement.HOME))
        c.markLoading(AdPlacement.HOME)
        assertFalse("no duplicate request while loading", c.shouldLoad(AdPlacement.HOME))
        val a = Ad(1); c.onLoaded(AdPlacement.HOME, a)
        now += 10 * min
        assertFalse("returning within 30 min reuses the ad", c.shouldLoad(AdPlacement.HOME))
        assertEquals(a, c.displayable(AdPlacement.HOME))
    }

    @Test fun refreshOnLaterVisitKeepsOldAdUntilReplaced() {
        val c = cache()
        val a = Ad(1); c.markLoading(AdPlacement.HOME); c.onLoaded(AdPlacement.HOME, a)
        now += 31 * min
        assertTrue(c.shouldLoad(AdPlacement.HOME))
        c.markLoading(AdPlacement.HOME)
        assertEquals("old ad stays visible while refreshing", a, c.displayable(AdPlacement.HOME))
        val b = Ad(2); c.onLoaded(AdPlacement.HOME, b)
        assertTrue("replaced ad is destroyed", a.destroyed)
        assertEquals(b, c.displayable(AdPlacement.HOME))
    }

    @Test fun expiredAdIsNeverShownAndIsDestroyed() {
        val c = cache()
        val a = Ad(1); c.markLoading(AdPlacement.SETTINGS); c.onLoaded(AdPlacement.SETTINGS, a)
        now += 56 * min
        assertNull(c.displayable(AdPlacement.SETTINGS))
        assertTrue(a.destroyed)
        assertTrue(c.shouldLoad(AdPlacement.SETTINGS))
    }

    @Test fun failureBacksOffAndFailedRefreshKeepsValidAd() {
        val c = cache()
        c.markLoading(AdPlacement.CONNECTION); c.onFailed(AdPlacement.CONNECTION, 3)
        assertNull(c.displayable(AdPlacement.CONNECTION))
        now += 1 * min
        assertFalse("no retry within the back-off", c.shouldLoad(AdPlacement.CONNECTION))
        now += 2 * min
        assertTrue(c.shouldLoad(AdPlacement.CONNECTION))

        val a = Ad(1); c.markLoading(AdPlacement.HOME); c.onLoaded(AdPlacement.HOME, a)
        now += 31 * min
        c.markLoading(AdPlacement.HOME); c.onFailed(AdPlacement.HOME, 3)
        assertEquals("failed refresh keeps the still-valid ad", a, c.displayable(AdPlacement.HOME))
        assertFalse(a.destroyed)
    }

    @Test fun placementsAreIndependentAndClearDestroysAll() {
        val c = cache()
        val a = Ad(1); val b = Ad(2)
        c.markLoading(AdPlacement.HOME); c.onLoaded(AdPlacement.HOME, a)
        c.markLoading(AdPlacement.SETTINGS); c.onLoaded(AdPlacement.SETTINGS, b)
        assertTrue(c.shouldLoad(AdPlacement.CONNECTION))
        c.clear()
        assertTrue(a.destroyed && b.destroyed)
        assertNull(c.displayable(AdPlacement.HOME))
    }

    @Test fun placementPlan() {
        // Diagnostics and TV setup never show ads.
        for (r in listOf(Route.DIAGNOSTICS, Route.TV_DEVICES)) {
            assertNull(AdPlacementPolicy.placementFor(r)); assertTrue(r in AdPlacementPolicy.excluded)
        }
        // Remotes: their own placements; the full-screen-control remotes use the compact layout.
        assertEquals(AdPlacement.PRESENTATION, AdPlacementPolicy.placementFor(Route.REMOTE))
        assertEquals(AdPlacement.PC_MOUSE, AdPlacementPolicy.placementFor(Route.PC_MOUSE))
        assertEquals(AdPlacement.TV, AdPlacementPolicy.placementFor(Route.TV))
        assertEquals(AdPlacement.MEDIA, AdPlacementPolicy.placementFor(Route.MEDIA))
        assertTrue("top-of-screen slots use the compact layout", AdPlacement.entries.all { it.compact })
        assertEquals("every placement has a distinct slot", AdPlacement.entries.size, AdPlacement.entries.toSet().size)
        assertEquals(AdPlacement.HOME, AdPlacementPolicy.placementFor(Route.HOME))
        assertFalse("no home ad during first-run setup", AdPlacementPolicy.homeAllowed(computerConfigured = false))
        assertFalse(AdPlacementPolicy.connectionAllowed(connecting = true, pairing = false))
        assertFalse(AdPlacementPolicy.connectionAllowed(connecting = false, pairing = true))
        assertTrue(AdPlacementPolicy.connectionAllowed(connecting = false, pairing = false))
        assertFalse(AdPlacementPolicy.settingsAllowed(calibrating = true))
    }
}
