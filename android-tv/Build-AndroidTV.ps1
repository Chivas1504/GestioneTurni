param(
    [string]$JavaHome = $env:JAVA_HOME,
    [string]$SdkRoot = $env:ANDROID_HOME,
    [string]$Gradle = "gradle",
    [switch]$Release
)
$ErrorActionPreference = "Stop"
if (-not $JavaHome -or -not (Test-Path -LiteralPath (Join-Path $JavaHome "bin/java.exe"))) {
    throw "Java JDK 17 o 21 non trovato. Installa Android Studio e usa la sua cartella jbr con -JavaHome."
}
if (-not $SdkRoot) { $SdkRoot = Join-Path $env:LOCALAPPDATA "Android/Sdk" }
if (-not (Test-Path -LiteralPath $SdkRoot)) { throw "Android SDK non trovato: usa -SdkRoot." }
$env:JAVA_HOME = $JavaHome
$env:ANDROID_HOME = $SdkRoot
$env:PATH = (Join-Path $JavaHome "bin") + ";" + $env:PATH
$env:GRADLE_USER_HOME = Join-Path $PSScriptRoot ".gradle-user"
if (-not (Get-Command $Gradle -ErrorAction SilentlyContinue)) {
    $cached = Get-ChildItem (Join-Path $env:USERPROFILE ".gradle/wrapper/dists/gradle-9.4.1-bin") -Recurse -Filter gradle.bat -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($cached) { $Gradle = $cached.FullName }
    else { throw "Gradle 9.4.1 non trovato. Apri il progetto in Android Studio oppure installa Gradle 9.4.1." }
}
$task = "assembleDebug"
if ($Release) {
    if (-not $env:TV_KEYSTORE -or -not $env:TV_STORE_PASSWORD -or -not $env:TV_KEY_ALIAS -or -not $env:TV_KEY_PASSWORD) {
        throw "Per la release configura TV_KEYSTORE, TV_STORE_PASSWORD, TV_KEY_ALIAS e TV_KEY_PASSWORD. Conserva la stessa chiave per gli aggiornamenti."
    }
    $task = "assembleRelease"
}
& $Gradle -p $PSScriptRoot --no-daemon $task lint test
if ($LASTEXITCODE -ne 0) { throw "Compilazione o controlli Android non riusciti." }
$variant = if ($Release) { "release" } else { "debug" }
$apk = Join-Path $PSScriptRoot "app/build/outputs/apk/$variant/app-$variant.apk"
if (-not (Test-Path -LiteralPath $apk)) { throw "APK non trovato dopo la compilazione." }
$output = Join-Path $PSScriptRoot "output"
New-Item -ItemType Directory -Force -Path $output | Out-Null
$destination = Join-Path $output "GestioneTurniTV-1.0.0-$variant.apk"
Copy-Item -LiteralPath $apk -Destination $destination -Force
Write-Output "APK pronto: $destination"
