#!/usr/bin/env bash
# Builds a minimal "Android SDK" containing only an apksigner drop-in (backed by
# Google's apksig library from Maven Central) so Godot can export & sign APKs
# without downloading the full SDK. Only needed for headless/CI builds; with a
# normal Android Studio SDK install you can skip this.
#
# Usage: tools/apksigner/setup_minimal_sdk.sh <sdk_dir>
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
SDK="${1:?usage: $0 <sdk_dir>}"
BT="$SDK/build-tools/35.0.0"
mkdir -p "$BT/lib" "$SDK/platform-tools" "$SDK/cmdline-tools/latest/bin"
# Set APKSIG_JAR=/path/to/apksig.jar to use a local copy instead of downloading.
if [ -n "${APKSIG_JAR:-}" ]; then
  cp "$APKSIG_JAR" "$BT/lib/apksig.jar"
elif ! unzip -tq "$BT/lib/apksig.jar" >/dev/null 2>&1; then
  curl -fsSL -o "$BT/lib/apksig.jar" \
    https://repo1.maven.org/maven2/com/android/tools/build/apksig/2.3.0/apksig-2.3.0.jar
fi
unzip -tq "$BT/lib/apksig.jar" >/dev/null || { echo "apksig.jar is not a valid jar" >&2; exit 1; }
mkdir -p "$BT/lib/classes"
javac -cp "$BT/lib/apksig.jar" -d "$BT/lib/classes" "$HERE/ApkSignCli.java"
cat > "$BT/apksigner" <<'SH'
#!/usr/bin/env bash
D="$(cd "$(dirname "$0")" && pwd)"
# apksig's v1 (JAR) signer uses JDK-internal sun.security classes.
exec java --add-exports java.base/sun.security.x509=ALL-UNNAMED \
  --add-exports java.base/sun.security.pkcs=ALL-UNNAMED \
  --add-exports java.base/sun.security.util=ALL-UNNAMED \
  -cp "$D/lib/apksig.jar:$D/lib/classes" ApkSignCli "$@"
SH
chmod +x "$BT/apksigner"
# Godot only checks these exist when validating the SDK path.
for f in "$SDK/platform-tools/adb" "$SDK/cmdline-tools/latest/bin/sdkmanager" "$BT/zipalign"; do
  [ -e "$f" ] || { printf '#!/bin/sh\necho "stub: %s not installed" >&2\nexit 1\n' "$(basename "$f")" > "$f"; chmod +x "$f"; }
done
echo "Minimal SDK ready at $SDK"
