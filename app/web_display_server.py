from __future__ import annotations

import json
import logging
import socket
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


LOGGER = logging.getLogger(__name__)

WEB_DISPLAY_PORT = 8080


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
        .card.doctor1 { border-top: 16px solid #2e7db8; }
        .card.doctor2 { border-top: 16px solid #2a9b6c; }
        .doctor-name { width: 100%; font-size: 56px; font-size: clamp(32px, 4vw, 70px); font-weight: 900; text-align: center; overflow-wrap: anywhere; }
        .called { width: 100%; color: #6c8192; font-size: 22px; font-size: clamp(15px, 1.4vw, 25px); font-weight: 800; letter-spacing: .18em; margin-top: 3vh; text-align: center; }
        .number { display: block; width: 100%; color: #145f91; font-size: 260px; font-size: clamp(170px, 25vh, 360px); line-height: .95; font-weight: 900; font-variant-numeric: tabular-nums; text-align: center; margin-left: 0; margin-right: 0; }
        .doctor2 .number { color: #167449; }
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
    <footer><span id="technical">Display automatico</span>&nbsp;&nbsp;·&nbsp;&nbsp;<span>Display 1.6.5</span></footer>
</div>
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

    function render(payload) {
        var state = payload && payload.state ? payload.state : {};
        var activeDoctors = [];
        var html = "";
        var serverLabel;
        var index;

        if (state.doctor1 && state.doctor1.queue_active) {
            activeDoctors.push(state.doctor1);
        }
        if (state.doctor2 && state.doctor2.queue_active) {
            activeDoctors.push(state.doctor2);
        }

        if (!activeDoctors.length) {
            content.id = "content";
            content.className = "empty";
            content.innerHTML = "<h1>In attesa</h1>" +
                "<p>Premendo Inizia coda sul PC, il display comparirà automaticamente.</p>";
        } else {
            content.id = "cards";
            content.className = "cards " + (activeDoctors.length === 1 ? "one" : "two");

            if (activeDoctors.length === 2) {
                html = "<table class=\"legacy-table\" width=\"100%\" height=\"100%\" cellspacing=\"12\" cellpadding=\"0\" border=\"0\" style=\"width:100%;height:100%;table-layout:fixed;border-collapse:separate;\">" +
                    "<tr>" +
                    "<td class=\"legacy-cell\" width=\"50%\" align=\"center\" valign=\"top\" style=\"width:50%;height:100%;text-align:center;vertical-align:top;padding:0;\">" + doctorCard(activeDoctors[0]) + "</td>" +
                    "<td class=\"legacy-cell\" width=\"50%\" align=\"center\" valign=\"top\" style=\"width:50%;height:100%;text-align:center;vertical-align:top;padding:0;\">" + doctorCard(activeDoctors[1]) + "</td>" +
                    "</tr></table>";
            } else {
                html = "<table width=\"100%\" height=\"100%\" cellspacing=\"0\" cellpadding=\"0\" border=\"0\" style=\"width:100%;height:100%;table-layout:fixed;\"><tr>" +
                    "<td width=\"16%\"></td>" +
                    "<td width=\"68%\" align=\"center\" valign=\"top\" style=\"width:68%;height:100%;text-align:center;vertical-align:top;\">" + doctorCard(activeDoctors[0]) + "</td>" +
                    "<td width=\"16%\"></td>" +
                    "</tr></table>";
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

    updateClock();
    window.setInterval(updateClock, 1000);
    poll();
    window.setInterval(poll, POLL_INTERVAL_MS);
})();
</script>
</body>
</html>
"""
