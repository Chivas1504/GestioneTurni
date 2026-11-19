package it.gestioneturni.tv;

import java.net.URI;
import java.util.List;

final class DiscoveryRules {
    interface Finder { String find(); }
    interface Probe { boolean reachable(String url); }
    static String resolve(boolean automatic, Finder finder, Probe probe, String last, String primary, String backup) {
        String found = automatic ? finder.find() : null;
        String[] candidates = automatic ? new String[]{found, last, primary, backup} : new String[]{primary, backup};
        for (String candidate : candidates) {
            String clean = candidate == null ? null : LocalAddress.normalise(candidate);
            if (clean != null && probe.reachable(clean)) return clean;
        }
        return null;
    }
    static String replyUrl(String type, String replyNonce, String expectedNonce, String sender) {
        if (!"GESTIONE_TURNI_SERVER".equals(type) || expectedNonce.isEmpty()
            || !expectedNonce.equals(replyNonce) || sender == null || sender.startsWith("127.")) return null;
        return LocalAddress.normalise(sender);
    }
    static String first(List<String> urls) {
        String result = null;
        long best = Long.MAX_VALUE;
        for (String url : urls) {
            String clean = LocalAddress.normalise(url);
            if (clean == null) continue;
            long value = 0;
            for (String part : URI.create(clean).getHost().split("\\.")) value = value * 256 + Integer.parseInt(part);
            if (value < best) { result = clean; best = value; }
        }
        return result;
    }
}
