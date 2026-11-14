package com.airpointer.remote.ads

import com.airpointer.remote.ui.Route

/**
 * Where native ads may appear: always at the TOP of the screen, so they are seen without
 * scrolling. Each placement has its own cached ad and ad unit. Top slots use the [compact]
 * layout (icon, attribution, headline, button): a tall media ad would push the screen's real
 * content below the fold, and a compact ad matches its loading placeholder, so nothing shifts
 * under the user's finger when it arrives.
 */
enum class AdPlacement(val compact: Boolean = true) {
    HOME, CONNECTION, SETTINGS, PRESENTATION, PC_MOUSE, TV, MEDIA,
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
        Route.REMOTE -> AdPlacement.PRESENTATION   // top, under the toolbar; thumbs work the bottom half
        Route.PC_MOUSE -> AdPlacement.PC_MOUSE     // top, above the mode tabs
        Route.TV -> AdPlacement.TV                 // top, above the TV keys
        Route.MEDIA -> AdPlacement.MEDIA           // top, above the player
        else -> null
    }

    /** Home: top of the page, only after first-run setup so onboarding stays clean. */
    fun homeAllowed(computerConfigured: Boolean) = computerConfigured

    /**
     * Connection: an ad does not *appear* while a connection or pairing is in progress. Discovery
     * scans are not a reason to hide it: the slot is at the top, and collapsing it mid-scan would
     * shift the list of computers the user is about to tap.
     */
    fun connectionAllowed(connecting: Boolean, pairing: Boolean) = !connecting && !pairing

    /** Sensitivity & calibration: no ad appears during a calibration (the phone must be held still). */
    fun settingsAllowed(calibrating: Boolean) = !calibrating
}
