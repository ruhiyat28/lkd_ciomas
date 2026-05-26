#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Clean ==="
flutter clean
flutter pub get

echo ""
echo "=== Build arm64-v8a Release APK (23MB) ==="
flutter build apk --release --target-platform android-arm64

APK="build/app/outputs/flutter-apk/app-release.apk"
cp "$APK" "./LKD-Ciomas-v1.0.0.apk"

echo ""
echo "=== Verify Signing ==="
~/Android/Sdk/build-tools/36.0.0/apksigner verify "$APK" && echo "SIGNED OK"

echo ""
echo "=== DONE ==="
ls -lh ./LKD-Ciomas-v1.0.0.apk
