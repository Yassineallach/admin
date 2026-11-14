package com.airpointer.remote.ads

import com.airpointer.remote.ui.Route

/**
 * Where native ads may appear. Each placement has its own cached ad and ad unit.
 * [compact] placements use the small layout (icon, headline, button — no media) on screens
 * whose controls fill the display.
 */
enum class AdPlacement(val compact: Boolean = false) {
    HOME, CONNECTION, SETTINGS,
    PRESENTATION(compact = true), PC_MOUSE(compact = true), TV, MEDIA,
}

/**
 * The placement plan as code (see README → Advertising). Ads sit where people browse or pause,
 * or — on the remotes — at the edge of the screen, separated from every control. Never in dialogs
 * or during an active pairing / discovery / connection / calibration step.
 */
object AdPlacementPolicy {
    /** Screens that never show ads, and why. */
    val excluded: Map<Route, String> = mapOf(
        Route.DIAGNOSTICS to "Diagnostics: troubleshooting context with live data",
        Route.TV_DEVICES to "TV setup: discovery and pairing flow",
    )

    fun placementFor(route: Route): AdPlacement? = when (route) {
        Route.HOME -> AdPlacement.HOME
        Route.PAIRING -> AdPlacement.CONNECTION
        Route.SETTINGS -> AdPlacement.SETTINGS
        // Remotes: kept clear of every control (AdMob prohibits ads that invite accidental clicks).
        Route.REMOTE -> AdPlacement.PRESENTATION   // compact, top of screen; thumbs work the bottom half
        Route.PC_MOUSE -> AdPlacement.PC_MOUSE     // compact, top of screen, above the mode tabs
        Route.TV -> AdPlacement.TV                 // end of the scroll, below every key
        Route.MEDIA -> AdPlacement.MEDIA           // end of the scroll, below playback controls
        else -> null
    }

    /** Home: bottom of the page, and only after first-run setup so onboarding stays clean. */
    fun homeAllowed(computerConfigured: Boolean) = computerConfigured

    /** Connection: only while nothing is in progress — never during discovery, pairing or connecting. */
    fun connectionAllowed(scanning: Boolean, connecting: Boolean, pairing: Boolean, dialogOpen: Boolean) =
        !scanning && !connecting && !pairing && !dialogOpen

    /** Sensitivity & calibration: not while calibrating (the phone must be held still). */
    fun settingsAllowed(calibrating: Boolean) = !calibrating
}
