package it.gestioneturni.tv;

import java.net.URI;

/** No DNS resolution: only private IPv4 display endpoints on port 8080. */
public final class LocalAddress {
    private LocalAddress() {}
    public static String normalise(String input) {
        String text = input.trim();
        if (!text.contains("://")) text = "http://" + text;
        try {
            URI uri = new URI(text);
            if (!"http".equals(uri.getScheme()) || uri.getUserInfo() != null || uri.getQuery() != null
                || uri.getFragment() != null || (uri.getPort() != -1 && uri.getPort() != 8080)
                || (uri.getPath() != null && !uri.getPath().isEmpty() && !uri.getPath().equals("/"))) return null;
            String host = uri.getHost();
            if (!privateIPv4(host)) return null;
            return "http://" + host + ":8080/";
        } catch (Exception error) { return null; }
    }
    public static boolean privateIPv4(String host) {
        if (host == null) return false;
        String[] parts = host.split("\\.", -1);
        if (parts.length != 4) return false;
        int[] n = new int[4];
        for (int i = 0; i < 4; i++) {
            if (!parts[i].matches("0|[1-9][0-9]{0,2}")) return false;
            n[i] = Integer.parseInt(parts[i]);
            if (n[i] > 255) return false;
        }
        return n[0] == 10 || (n[0] == 192 && n[1] == 168)
            || (n[0] == 172 && n[1] >= 16 && n[1] <= 31)
            || (n[0] == 169 && n[1] == 254) || n[0] == 127;
    }
    public static boolean permittedResource(String url) {
        try {
            URI uri = new URI(url);
            return "http".equals(uri.getScheme()) && privateIPv4(uri.getHost())
                && uri.getPort() == 8080 && uri.getUserInfo() == null;
        } catch (Exception error) { return false; }
    }
}
