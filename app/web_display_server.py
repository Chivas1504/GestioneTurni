from __future__ import annotations

import base64
import io
import json
import logging
import math
import socket
import struct
import threading
import wave
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


LOGGER = logging.getLogger(__name__)

WEB_DISPLAY_PORT = 8080


def _build_notification_wav() -> bytes:
    """Crea un breve ding WAV senza dipendenze esterne."""
    sample_rate = 22050
    duration = 0.32
    frequency = 880.0
    sample_count = int(sample_rate * duration)
    frames = bytearray()

    for index in range(sample_count):
        time_value = index / sample_rate
        envelope = max(0.0, 1.0 - (time_value / duration))
        value = int(32767 * 0.42 * envelope * math.sin(2.0 * math.pi * frequency * time_value))
        frames.extend(struct.pack("<h", value))

    output = io.BytesIO()
    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(bytes(frames))
    return output.getvalue()


NOTIFICATION_WAV = _build_notification_wav()

# MP3 incorporato per browser Smart TV che non riproducono WAV/PCM.
NOTIFICATION_MP3 = base64.b64decode(
    "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798YYcvjCxx/34+199+9Fiz8ow5L69vq63HejHew4w5j69+kr238gYzZcYp0Ld4YGCgmmMwzmKAXgQEjD8YjHUcDGUZjGcNDDIoTJ9BDa2TjnuCDT0jDFkbDGMLhCD5j8e5qYtZmuTRiiIhiGEBCBpuUnhacSo0SYLhuTnM+aQKwBjnGqkZ4yZwgDMUoBBJXQGjyXJRReVeSJqDrBZQuZMZY0ibisMsZxptrK7WuyGAmss5fmo7TOnenoi7TlRavDLkv7ZlT+v7LbkNP9D1qZhqHpduUxmW8FAEAosDAIKWaDAJJyIBCUTgUiixIBP/7ksT5gmZ+CP4PbY+EN7ag1dyaOUtNJEknNIkcOIkUWOJEtkkSSc0ijhxEjPOJEtc4lXmZyjSM+qrZOJU8kUcY1GWqq16rXk1HGmZ9VWvSRUFFQQXIKbCjgUVBBeBTYU2CmjJMQU1FMy4xMDCqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqqBotpfi6mEZpgG+ZBXBhBehnBiiDBth+CFiACAiHCOi7DRGQLONwcZtmScyJTCTRCfUDQFETiyjyCaRE4SBAZhNBEkacWUeYfef//////vRI04SBFmE0AkkCigMQLIE7j//5RIiKEgQsQTQRJLLHR7//5rLLHImWWVDZQwMEDCOgllBAwTo9llmRsoYGCBhAcAQSFhYXFRUVSBRUVFWf/x4qKsMVMQU1FMy4xMDBVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVX/+5LEiwPUdXaGJ5h3QAAANIAAAARVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVVV"
)


class _ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class WebDisplayServer:
    """Server HTTP di sola lettura per il display della Fire TV."""

    def __init__(
        self,
        *,
        state_provider: Callable[[], dict[str, dict[str, Any]]],
        role_provider: Callable[[], str],
        server_address_provider: Callable[[], str],
        local_address_provider: Callable[[], str],
        peer_addresses_provider: Callable[[], list[str]],
        port: int = WEB_DISPLAY_PORT,
    ) -> None:
        self._state_provider = state_provider
        self._role_provider = role_provider
        self._server_address_provider = server_address_provider
        self._local_address_provider = local_address_provider
        self._peer_addresses_provider = peer_addresses_provider
        self.port = int(port)

        self._lock = threading.RLock()
        self._http_server: _ReusableThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._http_server is not None

    def start(self) -> None:
        with self._lock:
            if self._http_server is not None:
                return

            handler_class = self._build_handler_class()

            try:
                http_server = _ReusableThreadingHTTPServer(
                    ("", self.port),
                    handler_class,
                )
            except OSError as error:
                LOGGER.error(
                    "Impossibile avviare il display web sulla porta %s: %s",
                    self.port,
                    error,
                )
                return

            self._http_server = http_server
            self._thread = threading.Thread(
                target=http_server.serve_forever,
                name="gestione-turni-web-display",
                daemon=True,
            )
            self._thread.start()

        LOGGER.info(
            "Display web avviato su http://%s:%s",
            self._local_address_provider(),
            self.port,
        )

    def stop(self) -> None:
        with self._lock:
            http_server = self._http_server
            thread = self._thread
            self._http_server = None
            self._thread = None

        if http_server is None:
            return

        http_server.shutdown()
        http_server.server_close()

        if thread is not None and thread.is_alive():
            thread.join(timeout=2.0)

        LOGGER.info("Display web arrestato")

    def get_display_url(self) -> str:
        return (
            f"http://{self._local_address_provider()}:{self.port}/"
        )

    def _build_handler_class(self):
        owner = self

        class DisplayRequestHandler(BaseHTTPRequestHandler):
            server_version = "GestioneTurniDisplay/1.0"

            def do_GET(self) -> None:  # noqa: N802
                path = urlparse(self.path).path

                if path in {"/", "/index.html"}:
                    self._send_html(DISPLAY_HTML)
                    return

                if path == "/api/state":
                    self._send_json(owner._build_payload())
                    return

                if path == "/health":
                    self._send_json({"status": "ok"})
                    return

                if path == "/turn.mp3":
                    self._send_bytes(
                        NOTIFICATION_MP3,
                        content_type="audio/mpeg",
                    )
                    return

                if path == "/turn.wav":
                    self._send_bytes(
                        NOTIFICATION_WAV,
                        content_type="audio/wav",
                    )
                    return

                if path == "/favicon.ico":
                    self.send_response(204)
                    self._send_common_headers(content_length=0)
                    self.end_headers()
                    return

                self._send_json(
                    {"error": "Risorsa non trovata"},
                    status_code=404,
                )

            def do_OPTIONS(self) -> None:  # noqa: N802
                self.send_response(204)
                self._send_common_headers(content_length=0)
                self.end_headers()

            def _send_html(self, content: str) -> None:
                encoded = content.encode("utf-8")
                self.send_response(200)
                self._send_common_headers(
                    content_type="text/html; charset=utf-8",
                    content_length=len(encoded),
                )
                self.end_headers()
                self.wfile.write(encoded)

            def _send_bytes(
                self,
                content: bytes,
                *,
                content_type: str,
                status_code: int = 200,
            ) -> None:
                self.send_response(status_code)
                self._send_common_headers(
                    content_type=content_type,
                    content_length=len(content),
                )
                self.end_headers()
                self.wfile.write(content)

            def _send_json(
                self,
                payload: dict[str, Any],
                *,
                status_code: int = 200,
            ) -> None:
                encoded = json.dumps(
                    payload,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")
                self.send_response(status_code)
                self._send_common_headers(
                    content_type="application/json; charset=utf-8",
                    content_length=len(encoded),
                )
                self.end_headers()
                self.wfile.write(encoded)

            def _send_common_headers(
                self,
                *,
                content_type: str | None = None,
                content_length: int | None = None,
            ) -> None:
                if content_type:
                    self.send_header("Content-Type", content_type)
                if content_length is not None:
                    self.send_header("Content-Length", str(content_length))

                self.send_header("Cache-Control", "no-store, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
                self.send_header("Access-Control-Allow-Headers", "Content-Type")
                self.send_header("Access-Control-Allow-Private-Network", "true")
                self.send_header("X-Content-Type-Options", "nosniff")

            def log_message(self, format_string: str, *args: object) -> None:
                LOGGER.debug(
                    "Display web %s - %s",
                    self.client_address[0],
                    format_string % args,
                )

        return DisplayRequestHandler

    def _build_payload(self) -> dict[str, Any]:
        local_address = self._clean_ip(
            self._local_address_provider()
        )
        server_address = self._clean_ip(
            self._server_address_provider()
        )

        candidates: list[str] = []
        for address in [
            local_address,
            server_address,
            *self._peer_addresses_provider(),
        ]:
            clean_address = self._clean_ip(address)
            if clean_address and clean_address not in candidates:
                candidates.append(clean_address)

        return {
            "application": "Gestione Turni",
            "role": str(self._role_provider()),
            "local_address": local_address,
            "server_address": server_address,
            "web_port": self.port,
            "candidates": candidates,
            "state": self._state_provider(),
        }

    @staticmethod
    def _clean_ip(value: object) -> str:
        address = str(value or "").strip()
        if not address or address == "0.0.0.0":
            return ""

        try:
            socket.inet_aton(address)
        except OSError:
            return ""

        return address


DISPLAY_HTML = r"""<!doctype html>
<html lang="it">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <meta name="theme-color" content="#0b2d47">
    <title>Gestione Turni</title>
    <style>
        :root { color-scheme: dark; font-family: Arial, Helvetica, sans-serif; }
        * { box-sizing: border-box; }
        html, body { width: 100%; height: 100%; margin: 0; overflow: hidden; }
        body {
            background: radial-gradient(circle at top, #154f73 0%, #0b2d47 50%, #061c2d 100%);
            color: #fff;
        }
        .screen { height: 100%; display: flex; flex-direction: column; padding: 3vh 4vw 2.5vh; }
        header { display: flex; display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; justify-content: space-between; min-height: 11vh; }
        .brand { font-size: 48px; font-size: clamp(30px, 3.2vw, 58px); font-weight: 900; letter-spacing: .08em; }
        .subtitle { color: #b9d8ec; font-size: 26px; font-size: clamp(18px, 1.5vw, 30px); text-align: center; }
        #clock { justify-self: end; font-size: 46px; font-size: clamp(30px, 3vw, 54px); font-weight: 800; font-variant-numeric: tabular-nums; }
        /* Layout legacy per browser Smart TV datati.
           Le due schede usano float: niente Grid, Flex o table-cell. */
        #cards {
            display: block;
            width: 100%;
            height: 76vh;
            min-height: 0;
            overflow: hidden;
        }
        #cards.one {
            display: block;
            padding: 0;
            text-align: center;
        }
        #cards.one .card {
            display: inline-block;
            width: 68%;
            height: 100%;
            vertical-align: top;
            float: none;
        }
        #cards.two {
            display: block;
            padding: 0;
        }
        #cards.two .card {
            display: block;
            width: 48.75%;
            height: 100%;
            vertical-align: top;
        }
        #cards.two .doctor1 {
            float: left;
        }
        #cards.two .doctor2 {
            float: right;
        }
        .card {
            background: #f7fafc;
            border-radius: 30px;
            color: #183b56;
            padding: 3vh 3vw;
            box-shadow: 0 22px 50px rgba(0,0,0,.25);
            min-width: 0;
            text-align: center;
            overflow: hidden;
        }
        .card { border-top: 16px solid #2e7db8; }
        .doctor-name { width: 100%; font-size: 56px; font-size: clamp(32px, 4vw, 70px); font-weight: 900; text-align: center; overflow-wrap: anywhere; }
        .called { width: 100%; color: #6c8192; font-size: 22px; font-size: clamp(15px, 1.4vw, 25px); font-weight: 800; letter-spacing: .18em; margin-top: 3vh; text-align: center; }
        .number { display: block; width: 100%; color: #145f91; font-size: 260px; font-size: clamp(170px, 25vh, 360px); line-height: .95; font-weight: 900; font-variant-numeric: tabular-nums; text-align: center; margin-left: 0; margin-right: 0; }
        .status { width: 100%; color: #60758a; font-size: 26px; font-size: clamp(18px, 1.7vw, 30px); font-weight: 600; text-align: center; }
        .empty, .connection {
            flex: 1; margin: 2vh 10vw; border: 1px solid rgba(255,255,255,.18); border-radius: 28px;
            display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
            background: rgba(255,255,255,.06); padding: 5vh 5vw;
        }
        .empty h1, .connection h1 { font-size: 64px; font-size: clamp(38px, 5vw, 80px); margin: 0 0 2vh; }
        .empty p, .connection p { color: #bddbf2; font-size: 32px; font-size: clamp(22px, 2.2vw, 38px); margin: 0; }
        footer { min-height: 7vh; display: flex; justify-content: center; align-items: flex-end; color: #dcecf8; font-size: 22px; font-size: clamp(16px, 1.5vw, 26px); }
        #technical { opacity: .75; }
        #audioButton {
            position: fixed;
            right: 2vw;
            bottom: 1.5vh;
            z-index: 20;
            border: 2px solid #ffffff;
            border-radius: 12px;
            background: #145f91;
            color: #ffffff;
            font-family: Arial, Helvetica, sans-serif;
            font-size: 18px;
            font-weight: 900;
            padding: 10px 18px;
            cursor: pointer;
        }
        #audioButton.enabled { background: #167449; }
        @media (max-width: 900px) {
            #cards.one .card { width: 78%; }
            #cards.two .card { width: 49%; }
            .screen { padding-left: 2vw; padding-right: 2vw; }
            .doctor-name { font-size: 30px; }
            .number { font-size: 150px; }
        }

        /* Layout critico Smart TV: vera tabella HTML, non CSS grid/flex/float. */
        .legacy-table { width: 100%; height: 76vh; border-collapse: separate; border-spacing: 12px 0; table-layout: fixed; }
        .legacy-cell { width: 50%; height: 100%; vertical-align: top; text-align: center; padding: 0; }
        .legacy-cell .card { width: 100%; height: 100%; display: block; float: none !important; margin: 0; text-align: center; }
        .legacy-number { width: 100%; text-align: center !important; margin-left: auto; margin-right: auto; }
    </style>
</head>
<body>
<div class="screen">
    <header>
        <div class="brand">GESTIONE TURNI</div>
        <div class="subtitle">Sala d'attesa</div>
        <div id="clock">--:--</div>
    </header>
    <main id="content" class="connection">
        <h1>Connessione in corso</h1>
        <p>Ricerca del computer che gestisce i turni…</p>
    </main>
    <footer><span id="technical">Display automatico</span>&nbsp;&nbsp;·&nbsp;&nbsp;<span>Display 1.6.8</span></footer>
</div>
<button id="audioButton" type="button">ATTIVA AUDIO</button>
<audio id="turnSound" preload="auto"><source src="/turn.mp3" type="audio/mpeg"><source src="/turn.wav" type="audio/wav"></audio>
<script>
(function () {
    "use strict";

    var STORAGE_KEY = "gestioneTurniDisplayCandidatesV1";
    var PORT = 8080;
    var POLL_INTERVAL_MS = 1000;
    var REQUEST_TIMEOUT_MS = 2500;
    var DISCONNECTED_AFTER_MS = 5000;

    var content = document.getElementById("content");
    var technical = document.getElementById("technical");
    var clock = document.getElementById("clock");
    var audioButton = document.getElementById("audioButton");
    var turnSound = document.getElementById("turnSound");

    var audioEnabled = false;
    var previousTurns = {};
    var previousTurnsReady = false;

    var currentOrigin = window.location.protocol + "//" + window.location.host;
    var activeBase = currentOrigin;
    var polling = false;
    var lastSuccessfulConnection = 0;
    var disconnectedVisible = false;

    function trimText(value) {
        return String(value || "").replace(/^\s+|\s+$/g, "");
    }

    function cleanHost(value) {
        var text = trimText(value);
        return /^\d{1,3}(\.\d{1,3}){3}$/.test(text) ? text : "";
    }

    function endpointFor(host) {
        return "http://" + host + ":" + PORT;
    }

    function contains(list, value) {
        var index;
        for (index = 0; index < list.length; index += 1) {
            if (list[index] === value) {
                return true;
            }
        }
        return false;
    }

    function uniqueValues(values, limit) {
        var result = [];
        var index;
        var value;

        for (index = 0; index < values.length; index += 1) {
            value = values[index];
            if (value && !contains(result, value)) {
                result.push(value);
                if (limit && result.length >= limit) {
                    break;
                }
            }
        }
        return result;
    }

    function loadCandidates() {
        var result = [currentOrigin];
        var stored;
        var index;

        try {
            stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
            if (Object.prototype.toString.call(stored) === "[object Array]") {
                for (index = 0; index < stored.length; index += 1) {
                    result.push(stored[index]);
                }
            }
        } catch (ignore) {}

        return uniqueValues(result, 8);
    }

    function saveCandidates(values) {
        var bases = [];
        var index;
        var host;
        var unique;

        values = values || [];

        for (index = 0; index < values.length; index += 1) {
            host = cleanHost(values[index]);
            if (host) {
                bases.push(endpointFor(host));
            }
        }

        bases.push(currentOrigin);
        bases.push(activeBase);
        unique = uniqueValues(bases, 8);

        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(unique));
        } catch (ignore) {}
    }

    function requestState(base, callback) {
        var xhr;
        var finished = false;
        var timeoutId;

        try {
            xhr = new XMLHttpRequest();
        } catch (error) {
            callback(null);
            return;
        }

        function finish(payload) {
            if (finished) {
                return;
            }
            finished = true;
            if (timeoutId) {
                window.clearTimeout(timeoutId);
            }
            callback(payload);
        }

        try {
            xhr.open("GET", base + "/api/state?t=" + new Date().getTime(), true);
            xhr.onreadystatechange = function () {
                var payload;

                if (xhr.readyState !== 4) {
                    return;
                }

                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        payload = JSON.parse(xhr.responseText);
                    } catch (error) {
                        payload = null;
                    }
                    finish(payload);
                } else {
                    finish(null);
                }
            };

            timeoutId = window.setTimeout(function () {
                try {
                    xhr.abort();
                } catch (ignore) {}
                finish(null);
            }, REQUEST_TIMEOUT_MS);

            xhr.send(null);
        } catch (error) {
            finish(null);
        }
    }

    function findServer(callback) {
        var queue = uniqueValues([activeBase].concat(loadCandidates()), 10);
        var visited = [];

        function next() {
            var base;

            if (!queue.length || visited.length >= 10) {
                callback(null);
                return;
            }

            base = queue.shift();

            if (!base || contains(visited, base)) {
                next();
                return;
            }

            visited.push(base);

            requestState(base, function (payload) {
                var candidates;
                var index;
                var host;
                var candidateBase;
                var serverHost;
                var serverBase;

                if (!payload) {
                    next();
                    return;
                }

                candidates = payload.candidates || [];
                saveCandidates(candidates);

                for (index = 0; index < candidates.length; index += 1) {
                    host = cleanHost(candidates[index]);
                    candidateBase = host ? endpointFor(host) : "";
                    if (candidateBase && !contains(visited, candidateBase) && !contains(queue, candidateBase)) {
                        queue.push(candidateBase);
                    }
                }

                serverHost = cleanHost(payload.server_address);
                if (serverHost) {
                    serverBase = endpointFor(serverHost);
                    if (!contains(visited, serverBase) && !contains(queue, serverBase)) {
                        queue.unshift(serverBase);
                    }
                }

                if (payload.role === "server") {
                    activeBase = base;
                    callback(payload);
                    return;
                }

                next();
            });
        }

        next();
    }

    function escapeHtml(value) {
        return String(value === null || typeof value === "undefined" ? "" : value)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/\"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function displayNumber(doctor) {
        var prefix = trimText(doctor.queue_prefix || "").toUpperCase().slice(0, 1);
        var number = parseInt(doctor.number, 10);

        if (isNaN(number) || number < 0) {
            number = 0;
        }

        return prefix + number;
    }

    function doctorCard(doctor) {
        return "<div class=\"card " + escapeHtml(doctor.doctor_id) + "\" style=\"width:100%;height:100%;text-align:center;float:none;margin:0;\">" +
            "<div class=\"doctor-name\" style=\"width:100%;text-align:center;\">" + escapeHtml(doctor.doctor_name || "Medico") + "</div>" +
            "<div class=\"called\" style=\"width:100%;text-align:center;\">NUMERO CHIAMATO</div>" +
            "<div class=\"number legacy-number\" align=\"center\" style=\"display:block;width:100%;text-align:center;margin-left:auto;margin-right:auto;\">" + escapeHtml(displayNumber(doctor)) + "</div>" +
            "<div class=\"status\" style=\"width:100%;text-align:center;\">Coda attiva</div>" +
            "</div>";
    }

    function enableAudio() {
        audioEnabled = true;
        audioButton.className = "enabled";
        audioButton.innerHTML = "AUDIO ATTIVO";

        /* Il click dell'utente sblocca l'audio. MP3 e' il formato
           principale per compatibilita con browser Smart TV datati. */
        try {
            turnSound.volume = 1.0;
            turnSound.load();
            turnSound.currentTime = 0;
            turnSound.play();
        } catch (ignore) {}
    }

    function playTurnSound() {
        if (!audioEnabled) {
            return;
        }

        try {
            turnSound.volume = 1.0;
            turnSound.pause();
            turnSound.currentTime = 0;
            turnSound.play();
        } catch (ignore) {}
    }

    function updateTurnSound(activeDoctors) {
        var nextTurns = {};
        var changed = false;
        var index;
        var doctor;
        var doctorId;
        var turnValue;

        for (index = 0; index < activeDoctors.length; index += 1) {
            doctor = activeDoctors[index];
            doctorId = trimText(doctor.doctor_id || ("doctor" + index));
            turnValue = displayNumber(doctor);
            nextTurns[doctorId] = turnValue;

            if (previousTurnsReady &&
                    typeof previousTurns[doctorId] !== "undefined" &&
                    previousTurns[doctorId] !== turnValue) {
                changed = true;
            }
        }

        previousTurns = nextTurns;
        previousTurnsReady = true;

        if (changed) {
            playTurnSound();
        }
    }

    function render(payload) {
        var state = payload && payload.state ? payload.state : {};
        var activeDoctors = [];
        var html = "";
        var serverLabel;
        var index;

        var stateKey;
        for (stateKey in state) {
            if (Object.prototype.hasOwnProperty.call(state, stateKey) && state[stateKey] && state[stateKey].queue_active) {
                activeDoctors.push(state[stateKey]);
            }
        }

        updateTurnSound(activeDoctors);

        if (!activeDoctors.length) {
            content.id = "content";
            content.className = "empty";
            content.innerHTML = "<h1>In attesa</h1>" +
                "<p>Premendo Inizia coda sul PC, il display comparirà automaticamente.</p>";
        } else {
            content.id = "cards";
            content.className = "cards " + (activeDoctors.length === 1 ? "one" : "two");

            if (activeDoctors.length === 1) {
                html = "<table width=\"100%\" height=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"width:100%;height:100%;table-layout:fixed;\"><tr>" +
                    "<td width=\"16%\"></td><td width=\"68%\" align=\"center\" valign=\"top\">" + doctorCard(activeDoctors[0]) + "</td><td width=\"16%\"></td></tr></table>";
            } else {
                var columns = activeDoctors.length === 2 ? 2 : 3;
                html = "<table class=\"legacy-table\" width=\"100%\" height=\"100%\" cellspacing=\"10\" cellpadding=\"0\" border=\"0\" style=\"width:100%;height:100%;table-layout:fixed;border-collapse:separate;\">";
                for (index = 0; index < activeDoctors.length; index += 1) {
                    if (index % columns === 0) { html += "<tr>"; }
                    html += "<td align=\"center\" valign=\"top\" style=\"text-align:center;vertical-align:top;padding:0;\">" + doctorCard(activeDoctors[index]) + "</td>";
                    if (index % columns === columns - 1 || index === activeDoctors.length - 1) { html += "</tr>"; }
                }
                html += "</table>";
            }
            content.innerHTML = html;
        }

        serverLabel = payload.server_address || payload.local_address || "locale";
        technical.innerHTML = "Connesso al server " + escapeHtml(serverLabel);
        disconnectedVisible = false;
    }

    function renderDisconnected() {
        if (disconnectedVisible) {
            return;
        }

        disconnectedVisible = true;
        content.id = "content";
        content.className = "connection";
        content.innerHTML = "<h1>Connessione in corso</h1>" +
            "<p>Il server sta cambiando oppure non è raggiungibile. Riprovo automaticamente…</p>";
        technical.innerHTML = "Ricerca automatica del server";
    }

    function poll() {
        if (polling) {
            return;
        }

        polling = true;

        findServer(function (payload) {
            var disconnectedFor;

            polling = false;

            if (payload) {
                lastSuccessfulConnection = new Date().getTime();
                render(payload);
                return;
            }

            disconnectedFor = new Date().getTime() - lastSuccessfulConnection;
            if (lastSuccessfulConnection === 0 || disconnectedFor >= DISCONNECTED_AFTER_MS) {
                renderDisconnected();
            }
        });
    }

    function twoDigits(value) {
        return value < 10 ? "0" + value : String(value);
    }

    function updateClock() {
        var now = new Date();
        clock.innerHTML = twoDigits(now.getHours()) + ":" + twoDigits(now.getMinutes());
    }

    audioButton.onclick = enableAudio;

    updateClock();
    window.setInterval(updateClock, 1000);
    poll();
    window.setInterval(poll, POLL_INTERVAL_MS);
})();
</script>
</body>
</html>
"""
