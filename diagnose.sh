#!/bin/bash
echo "=== Checking for common crash causes ==="
echo ""
echo "1. Duplicate attributes in layouts:"
grep -rn "android:textColor.*android:textColor" app/src/main/res/layout/ || echo "✓ No duplicate textColor"
echo ""
echo "2. Missing layout_width/height:"
grep -rn "android:textSize=" app/src/main/res/layout/activity_main.xml | grep -v "layout_width" | head -5
echo ""
echo "3. Checking theme references:"
grep -rn "theme" app/src/main/AndroidManifest.xml
echo ""
echo "4. Checking color resources:"
ls app/src/main/res/values/colors.xml && echo "✓ colors.xml exists"
echo ""
echo "5. Checking drawable resources:"
ls app/src/main/res/drawable/ | wc -l && echo "drawables found"
