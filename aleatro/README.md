# Aleatro

A roguelike of chance and combinations for Android, built with Godot 4.7.

Play poker hands to beat score targets across 8 floors. Each floor has a Minor Trial, a Major Trial and a Warden that bends one rule. Score is **Points × Mult**. Spend coins on charms, runes and sigils to build a scoring engine.

Six **challenge runs** change the rules: Glass Cannon, Pauper, One Shot, Royal Blood, Silent Suits and Snowblind. They're defined as data in `scripts/challenges.gd`, so adding one is a single entry.

All code, names, rules, numbers and art are original. Cards and UI are drawn in code, so the project has no image assets besides the icon.

## Project layout

| Path | What it holds |
|---|---|
| `scripts/run_state.gd` | Run state and rules: trials, wardens, economy, shop, sigils. Autoloaded as `Run`. |
| `scripts/hand_eval.gd` | Poker hand detection and base values per hand type |
| `scripts/scoring.gd` | Scoring pipeline: hand base → scored cards → held cards → charms, left to right |
| `scripts/charms.gd` | The 22 charms and their scoring hooks |
| `scripts/challenges.gd` | Challenge runs and the rules each one changes |
| `scripts/main.gd` | All screens, built in code, plus the scoring animations |
| `scripts/card_view.gd`, `scripts/charm_view.gd` | Card and charm widgets |
| `tests/run_tests.gd` | Headless unit tests, plus simulated bot runs of the standard game and every challenge |
| `tests/shots.tscn` | Renders every screen to `build/shots/` |

## Run the tests

```bash
godot --headless --path . --import
godot --headless --path . -s res://tests/run_tests.gd
```

## Build the Android APK

You need the Godot 4.7 export templates, the Android SDK (build-tools and platform-tools), JDK 17 or later, and a keystore.

```bash
godot --headless --path . --export-debug "Android" build/Aleatro.apk
```

- **Package:** `com.mardev.Aleatro`
- **Architectures:** arm64-v8a and armeabi-v7a
- **Display:** landscape (either way up), immersive mode

### Release builds

Debug APKs are signed with a debug key. For a release build:

1. Create your own keystore and keep it safe. You need the same key for every future update.
2. In Godot, open **Project → Export → Android** and set the release keystore.
3. Run `--export-release`.

Google Play requires an AAB, not an APK. To build one, enable **Use Gradle Build**, install the Android build template, and set the export format to AAB.
