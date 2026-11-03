package com.airpointer.remote.presenter

/** Every action that can be bound to a button, gesture or physical key. */
enum class RemoteAction(val label: String) {
    NONE("Do nothing"),
    NEXT_SLIDE("Next slide"),
    PREVIOUS_SLIDE("Previous slide"),
    LEFT_CLICK("Left click"),
    RIGHT_CLICK("Right click"),
    TOGGLE_POINTER("Toggle pointer"),
    RECENTER("Recenter cursor"),
    PAUSE_TRACKING("Pause / resume tracking"),
    START_SLIDESHOW("Start slideshow (F5)"),
    START_FROM_CURRENT("Start from current slide (Shift+F5)"),
    END_SLIDESHOW("End slideshow (Esc)"),
    BLACK_SCREEN("Black screen (B)"),
    WHITE_SCREEN("White screen (W)"),
    LASER_POINTER("PowerPoint laser (Ctrl+L)"),
    SCROLL_UP("Scroll up"),
    SCROLL_DOWN("Scroll down"),
}

enum class PointerMode(val label: String) {
    TOGGLE("Tap to toggle"),
    HOLD("Hold to point"),
}

enum class SlideKeys(val label: String) {
    ARROWS("Arrow keys"),
    PAGE_KEYS("Page Up / Page Down"),
}
