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
        header { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; min-height: 11vh; }
        .brand { font-size: clamp(30px, 3.2vw, 58px); font-weight: 900; letter-spacing: .08em; }
        .subtitle { color: #b9d8ec; font-size: clamp(18px, 1.5vw, 30px); text-align: center; }
        #clock { justify-self: end; font-size: clamp(30px, 3vw, 54px); font-weight: 800; font-variant-numeric: tabular-nums; }
        #cards { flex: 1; display: grid; gap: 2.5vw; align-items: stretch; min-height: 0; }
        #cards.one { grid-template-columns: minmax(0, 1fr); padding: 0 16vw; }
        #cards.two { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .card {
            background: #f7fafc;
            border-radius: 30px;
            color: #183b56;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 3vh 3vw;
            box-shadow: 0 22px 50px rgba(0,0,0,.25);
            min-width: 0;
        }
        .card.doctor1 { border-top: 16px solid #2e7db8; }
        .card.doctor2 { border-top: 16px solid #2a9b6c; }
        .doctor-name { font-size: clamp(32px, 4vw, 70px); font-weight: 900; text-align: center; overflow-wrap: anywhere; }
        .called { color: #6c8192; font-size: clamp(15px, 1.4vw, 25px); font-weight: 800; letter-spacing: .18em; margin-top: 3vh; }
        .number { color: #145f91; font-size: clamp(170px, 25vh, 360px); line-height: .95; font-weight: 900; font-variant-numeric: tabular-nums; }
        .doctor2 .number { color: #167449; }
        .status { color: #60758a; font-size: clamp(18px, 1.7vw, 30px); font-weight: 600; }
        .empty, .connection {
            flex: 1; margin: 2vh 10vw; border: 1px solid rgba(255,255,255,.18); border-radius: 28px;
            display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center;
            background: rgba(255,255,255,.06); padding: 5vh 5vw;
        }
        .empty h1, .connection h1 { font-size: clamp(38px, 5vw, 80px); margin: 0 0 2vh; }
        .empty p, .connection p { color: #bddbf2; font-size: clamp(22px, 2.2vw, 38px); margin: 0; }
        footer { min-height: 7vh; display: flex; justify-content: center; align-items: end; color: #dcecf8; font-size: clamp(16px, 1.5vw, 26px); }
        #technical { opacity: .75; }
        @media (max-width: 900px) {
            #cards.one { padding: 0; }
            .screen { padding-left: 3vw; padding-right: 3vw; }
        }
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
    <footer><span id="technical">Display automatico</span></footer>
</div>
<script>
(() => {
    const STORAGE_KEY = "gestioneTurniDisplayCandidatesV1";
    const PORT = 8080;

    const POLL_INTERVAL_MS = 1000;
    const REQUEST_TIMEOUT_MS = 2500;
    const DISCONNECTED_AFTER_MS = 5000;

    const content = document.getElementById("content");
    const technical = document.getElementById("technical");

    let activeBase = window.location.origin;
    let polling = false;
    let lastSuccessfulConnection = 0;
    let disconnectedVisible = false;

    const cleanHost = value => {
        const text = String(value || "").trim();
        return /^\d{1,3}(\.\d{1,3}){3}$/.test(text) ? text : "";
    };

    const endpointFor = host => `http://${host}:${PORT}`;

    const loadCandidates = () => {
        const result = [window.location.origin];

        try {
            const stored = JSON.parse(
                localStorage.getItem(STORAGE_KEY) || "[]"
            );

            if (Array.isArray(stored)) {
                result.push(...stored);
            }
        } catch (_) {}

        return [...new Set(result.filter(Boolean))];
    };

    const saveCandidates = values => {
        const bases = [];

        for (const value of values || []) {
            const host = cleanHost(value);

            if (host) {
                bases.push(endpointFor(host));
            }
        }

        bases.push(window.location.origin, activeBase);

        const unique = [...new Set(
            bases.filter(Boolean)
        )].slice(0, 8);

        try {
            localStorage.setItem(
                STORAGE_KEY,
                JSON.stringify(unique)
            );
        } catch (_) {}
    };

    const fetchState = async base => {
        const controller = new AbortController();

        const timeout = setTimeout(
            () => controller.abort(),
            REQUEST_TIMEOUT_MS
        );

        try {
            const response = await fetch(
                `${base}/api/state?t=${Date.now()}`,
                {
                    cache: "no-store",
                    signal: controller.signal
                }
            );

            if (!response.ok) {
                return null;
            }

            return await response.json();
        } catch (_) {
            return null;
        } finally {
            clearTimeout(timeout);
        }
    };

    const findServer = async () => {
        const initialBases = [
            activeBase,
            ...loadCandidates()
        ];

        const visited = new Set();

        const queue = [
            ...new Set(initialBases.filter(Boolean))
        ];

        while (queue.length && visited.size < 10) {
            const base = queue.shift();

            if (!base || visited.has(base)) {
                continue;
            }

            visited.add(base);

            const payload = await fetchState(base);

            if (!payload) {
                continue;
            }

            saveCandidates(payload.candidates);

            for (const address of payload.candidates || []) {
                const host = cleanHost(address);
                const candidateBase = host
                    ? endpointFor(host)
                    : "";

                if (
                    candidateBase &&
                    !visited.has(candidateBase)
                ) {
                    queue.push(candidateBase);
                }
            }

            const serverHost = cleanHost(
                payload.server_address
            );

            if (serverHost) {
                const serverBase = endpointFor(serverHost);

                if (!visited.has(serverBase)) {
                    queue.unshift(serverBase);
                }
            }

            if (payload.role === "server") {
                activeBase = base;
                return payload;
            }
        }

        return null;
    };

    const escapeHtml = value => String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

    const doctorCard = doctor => `
        <section class="card ${escapeHtml(doctor.doctor_id)}">
            <div class="doctor-name">
                ${escapeHtml(
                    doctor.doctor_name || "Medico"
                )}
            </div>

            <div class="called">
                NUMERO CHIAMATO
            </div>

            <div class="number">
                ${escapeHtml(
                    `${String(doctor.queue_prefix || "").trim().toUpperCase().slice(0, 1)}${
                        Number.isFinite(Number(doctor.number))
                            ? Math.max(0, parseInt(doctor.number, 10))
                            : 0
                    }`
                )}
            </div>

            <div class="status">
                Coda attiva
            </div>
        </section>
    `;

    const render = payload => {
        const state = payload && payload.state
            ? payload.state
            : {};

        const activeDoctors = [
            state.doctor1,
            state.doctor2
        ].filter(
            doctor => doctor && doctor.queue_active
        );

        if (!activeDoctors.length) {
            content.id = "content";
            content.className = "empty";

            content.innerHTML = `
                <h1>In attesa</h1>
                <p>
                    Premendo Inizia coda sul PC,
                    il display comparirà automaticamente.
                </p>
            `;
        } else {
            content.id = "cards";

            content.className = `cards ${
                activeDoctors.length === 1
                    ? "one"
                    : "two"
            }`;

            content.innerHTML = activeDoctors
                .map(doctorCard)
                .join("");
        }

        technical.textContent =
            `Connesso al server ${
                payload.server_address ||
                payload.local_address ||
                "locale"
            }`;

        disconnectedVisible = false;
    };

    const renderDisconnected = () => {
        if (disconnectedVisible) {
            return;
        }

        disconnectedVisible = true;

        content.id = "content";
        content.className = "connection";

        content.innerHTML = `
            <h1>Connessione in corso</h1>
            <p>
                Il server sta cambiando oppure non è
                raggiungibile. Riprovo automaticamente…
            </p>
        `;

        technical.textContent =
            "Ricerca automatica del server";
    };

    const poll = async () => {
        if (polling) {
            return;
        }

        polling = true;

        try {
            const payload = await findServer();

            if (payload) {
                lastSuccessfulConnection = Date.now();
                render(payload);
                return;
            }

            const disconnectedFor =
                Date.now() - lastSuccessfulConnection;

            if (
                lastSuccessfulConnection === 0 ||
                disconnectedFor >= DISCONNECTED_AFTER_MS
            ) {
                renderDisconnected();
            }
        } finally {
            polling = false;
        }
    };

    const updateClock = () => {
        document.getElementById(
            "clock"
        ).textContent = new Date().toLocaleTimeString(
            "it-IT",
            {
                hour: "2-digit",
                minute: "2-digit"
            }
        );
    };

    updateClock();

    setInterval(
        updateClock,
        1000
    );

    poll();

    setInterval(
        poll,
        POLL_INTERVAL_MS
    );
})();
</script>
</body>
</html>
"""
