package it.gestioneturni.tv;

import java.net.*;
import java.nio.charset.StandardCharsets;
import java.util.*;
import org.json.JSONObject;

/** Uses the existing desktop discovery protocol; no PC update is required. */
final class ServerDiscovery {
    static String discover() {
        String nonce = UUID.randomUUID().toString();
        List<String> candidates = new ArrayList<>();
        try (DatagramSocket socket = new DatagramSocket()) {
            socket.setBroadcast(true);
            socket.setSoTimeout(250);
            byte[] request = new JSONObject().put("type", "GESTIONE_TURNI_DISCOVER")
                .put("doctor_id", "tv-display").put("nonce", nonce).toString().getBytes(StandardCharsets.UTF_8);
            Set<InetAddress> targets = new HashSet<>();
            targets.add(InetAddress.getByName("255.255.255.255"));
            for (NetworkInterface network : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                if (!network.isUp() || network.isLoopback()) continue;
                for (InterfaceAddress address : network.getInterfaceAddresses())
                    if (address.getBroadcast() != null) targets.add(address.getBroadcast());
            }
            for (InetAddress target : targets) {
                try { socket.send(new DatagramPacket(request, request.length, target, 50555)); }
                catch (Exception ignored) { }
            }
            long deadline = System.nanoTime() + 1500000000L;
            while (System.nanoTime() < deadline) {
                DatagramPacket reply = new DatagramPacket(new byte[4096], 4096);
                try {
                    socket.receive(reply);
                    JSONObject data = new JSONObject(new String(reply.getData(), 0, reply.getLength(), StandardCharsets.UTF_8));
                    String url = DiscoveryRules.replyUrl(data.optString("type"), data.optString("nonce"), nonce,
                        reply.getAddress().getHostAddress());
                    if (url != null) candidates.add(url);
                } catch (SocketTimeoutException ignored) { }
                catch (Exception ignored) { }
            }
        } catch (Exception ignored) { }
        return DiscoveryRules.first(candidates);
    }
    static boolean reachable(String base) {
        if (base == null || LocalAddress.normalise(base) == null) return false;
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(base + "api/state").openConnection();
            connection.setConnectTimeout(1500);
            connection.setReadTimeout(1500);
            connection.setInstanceFollowRedirects(false);
            if (connection.getResponseCode() != 200) return false;
            try (java.io.InputStream stream = connection.getInputStream()) {
                java.io.ByteArrayOutputStream bytes = new java.io.ByteArrayOutputStream();
                byte[] chunk = new byte[4096];
                int count;
                while ((count = stream.read(chunk)) != -1) {
                    if (bytes.size() + count > 4 * 1024 * 1024) return false;
                    bytes.write(chunk, 0, count);
                }
                JSONObject payload = new JSONObject(bytes.toString("UTF-8"));
                return "Gestione Turni".equals(payload.optString("application")) && payload.optJSONObject("state") != null;
            }
        } catch (Exception ignored) { return false; }
        finally { if (connection != null) connection.disconnect(); }
    }
}
