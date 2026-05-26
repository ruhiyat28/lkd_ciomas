# Flutter ProGuard Rules
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.**  { *; }
-keep class io.flutter.util.**  { *; }
-keep class io.flutter.view.**  { *; }
-keep class io.flutter.**  { *; }
-keep class io.flutter.plugins.**  { *; }
-keep class com.lkdciomas.** { *; }
-keep class * extends java.util.ListResourceBundle {
    protected Object[][] getContents();
}
-dontwarn com.google.errorprone.annotations.*
-dontwarn javax.annotation.**
