"""Build a signed APK using installed SDK/JDK tools, without a Gradle daemon.

Uses cached AAPT2 and JUnit artifacts; does not download or install dependencies.
All generated files stay inside the project. Signing material is private and
ignored by Git; retain it to sign subsequent updates of the same application.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import secrets
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
ANDROID = "http://schemas.android.com/apk/res/android"


def run(args, *, env=None):
    result = subprocess.run([str(arg) for arg in args], env=env, cwd=PROJECT)
    if result.returncode:
        raise RuntimeError(f"{Path(str(args[0])).name} non riuscito (codice {result.returncode}).")


def cached(cache: Path, pattern: str) -> Path:
    matches = sorted(cache.glob(pattern))
    if not matches:
        raise RuntimeError("Dipendenza non presente nella cache: " + pattern)
    return matches[-1].resolve()


def align_zip(source: Path, destination: Path) -> None:
    """Align uncompressed ZIP entries to four bytes before APK signing.

    This APK contains no native .so libraries. Unknown extra field 0xFFFF is
    padding only; the Android SDK's zipalign checker verifies the final result.
    """
    with zipfile.ZipFile(source) as incoming, zipfile.ZipFile(destination, "w") as outgoing:
        for entry in incoming.infolist():
            info = zipfile.ZipInfo(entry.filename, entry.date_time)
            info.compress_type = entry.compress_type
            info.external_attr = entry.external_attr
            if info.compress_type == zipfile.ZIP_STORED:
                offset = outgoing.fp.tell() + 30 + len(info.filename.encode("utf-8"))
                padding = (-offset) % 4
                if padding:
                    info.extra = struct.pack("<HH", 0xFFFF, padding) + bytes(padding)
            outgoing.writestr(info, incoming.read(entry))


def verify_alignment(apk: Path) -> None:
    with apk.open("rb") as raw, zipfile.ZipFile(apk) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Archivio APK danneggiato.")
        for entry in archive.infolist():
            if entry.compress_type == zipfile.ZIP_STORED:
                raw.seek(entry.header_offset + 26)
                name_length, extra_length = struct.unpack("<HH", raw.read(4))
                if (entry.header_offset + 30 + name_length + extra_length) % 4:
                    raise RuntimeError("Entry APK non allineata: " + entry.filename)


def build(java_home: Path, sdk: Path, cache: Path):
    java, javac, keytool = [java_home / "bin" / (name + ".exe") for name in ["java", "javac", "keytool"]]
    if not all(path.is_file() for path in [java, javac, keytool]):
        raise RuntimeError("JDK incompleto: servono java, javac e keytool.")
    tools = sdk / "build-tools" / "36.0.0"
    platform = next((sdk / "platforms" / version / "android.jar" for version in ["android-36", "android-36.1"]
                     if (sdk / "platforms" / version / "android.jar").is_file()), None)
    if platform is None or not tools.is_dir():
        raise RuntimeError("Servono Android SDK Platform 36 e Build Tools 36.0.0.")

    build_dir = PROJECT / ".tools" / "android-build"
    classes, tests, compiled_res, dex_dir = [build_dir / name for name in ["classes", "tests", "resources", "dex"]]
    for path in [classes, tests, compiled_res, dex_dir]:
        path.mkdir(parents=True, exist_ok=True)

    aapt_jar = cached(cache, "modules-2/files-2.1/com.android.tools.build/aapt2/9.2.1-*/*/*-windows.jar")
    aapt_dir = build_dir / "aapt2"
    aapt_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(aapt_jar) as archive:
        (aapt_dir / "aapt2.exe").write_bytes(archive.read("aapt2.exe"))
    aapt = aapt_dir / "aapt2.exe"
    print("Compilazione risorse Android...", flush=True)
    resources = ROOT / "app/src/main/res"
    flats = []
    for resource in sorted(resources.rglob("*")):
        if not resource.is_file():
            continue
        # Absolute Windows paths are necessary for native AAPT2 resource parsing.
        run([aapt, "compile", "--no-crunch", resource.resolve(), "-o", compiled_res.resolve()])
        flats.append(compiled_res / (resource.parent.name + "_" + resource.name + ".flat"))

    ET.register_namespace("android", ANDROID)
    manifest = ET.parse(ROOT / "app/src/main/AndroidManifest.xml")
    root = manifest.getroot()
    root.set("package", "it.gestioneturni.tv")
    root.set("{" + ANDROID + "}versionCode", "2")
    root.set("{" + ANDROID + "}versionName", "1.1.0")
    uses_sdk = ET.Element("uses-sdk", {"{" + ANDROID + "}minSdkVersion": "23",
                                      "{" + ANDROID + "}targetSdkVersion": "36"})
    root.insert(0, uses_sdk)
    manifest_file = build_dir / "AndroidManifest.xml"
    manifest.write(manifest_file, encoding="utf-8", xml_declaration=True)
    unsigned = build_dir / "unsigned.apk"
    linked = build_dir / "linked-resources"
    linked.mkdir(exist_ok=True)
    for resource in resources.rglob("*"):
        if resource.is_file():
            (linked / "res" / resource.parent.name).mkdir(parents=True, exist_ok=True)
    # Directory output also avoids native ZIP-writer failures in restricted hosts.
    # Python packages the compiled resources with the standard ZIP implementation.
    run([aapt, "link", "--output-to-dir", "--manifest", manifest_file, "-I", platform, "-o", linked, *flats])
    with zipfile.ZipFile(unsigned, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(linked.rglob("*")):
            if source.is_file():
                compression = zipfile.ZIP_STORED if source.name == "resources.arsc" else zipfile.ZIP_DEFLATED
                archive.write(source, source.relative_to(linked).as_posix(), compress_type=compression)

    print("Compilazione Java dell'app...", flush=True)
    sources = sorted((ROOT / "app/src/main/java").rglob("*.java"))
    run([javac, "--release", "17", "-encoding", "UTF-8", "-cp", platform, "-d", classes, *sources])

    junit = cached(cache, "modules-2/files-2.1/junit/junit/4.13.2/*/junit-4.13.2.jar")
    hamcrest = cached(cache, "modules-2/files-2.1/org.hamcrest/hamcrest-core/1.3/*/hamcrest-core-1.3.jar")
    cp = os.pathsep.join(str(path) for path in [platform, classes, junit, hamcrest])
    test_sources = sorted((ROOT / "app/src/test/java").rglob("*.java"))
    run([javac, "--release", "17", "-encoding", "UTF-8", "-cp", cp, "-d", tests, *test_sources])
    print("Test Java Android...", flush=True)
    run([java, "-cp", os.pathsep.join(str(path) for path in [classes, tests, junit, hamcrest]),
         "org.junit.runner.JUnitCore", "it.gestioneturni.tv.LocalAddressTest", "it.gestioneturni.tv.DiscoveryRulesTest"])

    classes_jar = build_dir / "classes.jar"
    with zipfile.ZipFile(classes_jar, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(classes.rglob("*.class")):
            archive.write(source, source.relative_to(classes).as_posix())
    run([java, "-cp", tools / "lib/d8.jar", "com.android.tools.r8.D8", "--release", "--min-api", "23",
         "--lib", platform, "--output", dex_dir, classes_jar])
    with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for source in sorted(dex_dir.glob("classes*.dex")):
            archive.write(source, source.name)
    aligned = build_dir / "aligned.apk"
    align_zip(unsigned, aligned)
    verify_alignment(aligned)

    signing = ROOT / "private-signing"
    signing.mkdir(exist_ok=True)
    keystore, password_file = signing / "gestioneturni-tv.p12", signing / "password.txt"
    if keystore.exists() and not password_file.exists():
        raise RuntimeError("Password della chiave esistente non trovata; non viene generata una nuova firma.")
    if not password_file.exists():
        with password_file.open("x", encoding="ascii") as file:
            file.write(secrets.token_urlsafe(32))
    signing_env = os.environ.copy()
    signing_env["GESTIONE_TV_SIGN_PASSWORD"] = password_file.read_text(encoding="ascii").strip()
    if not keystore.exists():
        run([keytool, "-genkeypair", "-alias", "gestioneturni-tv", "-keyalg", "RSA", "-keysize", "2048",
             "-validity", "10000", "-dname", "CN=Gestione Turni TV, O=Gestione Turni, C=IT",
             "-storetype", "PKCS12", "-keystore", keystore,
             "-storepass:env", "GESTIONE_TV_SIGN_PASSWORD", "-keypass:env", "GESTIONE_TV_SIGN_PASSWORD"], env=signing_env)
    output = ROOT / "output" / "GestioneTurniTV-1.1.0.apk"
    output.parent.mkdir(exist_ok=True)
    apksigner = [java, "-jar", tools / "lib/apksigner.jar"]
    run([*apksigner, "sign", "--ks", keystore, "--ks-key-alias", "gestioneturni-tv",
         "--ks-pass", "env:GESTIONE_TV_SIGN_PASSWORD", "--key-pass", "env:GESTIONE_TV_SIGN_PASSWORD",
         "--out", output, aligned], env=signing_env)
    run([*apksigner, "verify", "--verbose", "--print-certs", output])
    verify_alignment(output)
    run([tools / "zipalign.exe", "-c", "4", output])
    run([aapt, "dump", "badging", output])
    print("APK firmato pronto: " + str(output), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--sdk-root", type=Path, default=Path.home() / "AppData/Local/Android/Sdk")
    parser.add_argument("--gradle-cache", type=Path, default=Path.home() / ".gradle/caches")
    args = parser.parse_args()
    try:
        build(args.java_home.resolve(), args.sdk_root.resolve(), args.gradle_cache.resolve())
    except (OSError, RuntimeError) as error:
        print("Compilazione interrotta: " + str(error), file=sys.stderr)
        sys.exit(1)
