package com.airpointer.remote.ads

import com.airpointer.remote.ui.Route

/** Where native ads may appear. Each placement has its own cached ad and ad unit. */
enum class AdPlacement { HOME, CONNECTION, SETTINGS }

/**
 * The placement plan as code (see README → Advertising). User experience first:
 * ads only where people browse or pause, never inside remotes, dialogs or an active
 * pairing / discovery / connection / calibration step.
 */
object AdPlacementPolicy {
    /** Screens that never show ads, and why. */
    val excluded: Map<Route, String> = mapOf(
        Route.REMOTE to "Presentation remote: main interaction area, accidental taps during a talk",
        Route.PC_MOUSE to "PC Mouse: touchpad/gesture surface fills the screen",
        Route.TV to "TV Remote: D-pad and keys, gesture-heavy",
        Route.MEDIA to "Media Player: playback controls and seek bar",
        Route.DIAGNOSTICS to "Diagnostics: troubleshooting context with live data",
        Route.TV_DEVICES to "TV setup: discovery and pairing flow",
    )

    fun placementFor(route: Route): AdPlacement? = when (route) {
        Route.HOME -> AdPlacement.HOME
        Route.PAIRING -> AdPlacement.CONNECTION
        Route.SETTINGS -> AdPlacement.SETTINGS
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
