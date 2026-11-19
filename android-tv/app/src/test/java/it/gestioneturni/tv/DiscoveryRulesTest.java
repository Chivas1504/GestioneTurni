package it.gestioneturni.tv;
import org.junit.Test;
import static org.junit.Assert.*;
import java.util.Arrays;
public class DiscoveryRulesTest {
    @Test public void startupNeedsNoSavedAddress() {
        assertEquals("http://192.168.1.10:8080/", DiscoveryRules.resolve(true,
            () -> "192.168.1.10", url -> true, "", "", ""));
    }
    @Test public void oldAddressDoesNotOverrideNewServer() {
        assertEquals("http://192.168.1.25:8080/", DiscoveryRules.resolve(true,
            () -> "192.168.1.25", url -> true, "192.168.1.10", "192.168.1.10", ""));
    }
    @Test public void waitsWhenEveryPcIsOffAndFindsLaterStartup() {
        assertNull(DiscoveryRules.resolve(true, () -> null, url -> false, "192.168.1.10", "", ""));
        assertEquals("http://192.168.1.25:8080/", DiscoveryRules.resolve(true,
            () -> "192.168.1.25", url -> true, "192.168.1.10", "", ""));
    }
    @Test public void savedServerWorksWhenBroadcastIsUnavailable() {
        assertEquals("http://192.168.1.10:8080/", DiscoveryRules.resolve(true,
            () -> null, url -> true, "192.168.1.10", "", ""));
    }
    @Test public void manualModeUsesBackupWithoutDiscovery() {
        assertEquals("http://192.168.1.25:8080/", DiscoveryRules.resolve(false,
            () -> { fail("Manual mode must not broadcast"); return null; },
            url -> url.contains(".25:"), "", "192.168.1.10", "192.168.1.25"));
    }
    @Test public void acceptsExistingDesktopProtocol() {
        assertEquals("http://192.168.1.10:8080/", DiscoveryRules.replyUrl("GESTIONE_TURNI_SERVER", "nonce", "nonce", "192.168.1.10"));
    }
    @Test public void rejectsUnrelatedOrOldReplies() {
        assertNull(DiscoveryRules.replyUrl("OTHER", "nonce", "nonce", "192.168.1.10"));
        assertNull(DiscoveryRules.replyUrl("GESTIONE_TURNI_SERVER", "old", "nonce", "192.168.1.10"));
        assertNull(DiscoveryRules.replyUrl("GESTIONE_TURNI_SERVER", "nonce", "nonce", "8.8.8.8"));
        assertNull(DiscoveryRules.replyUrl("GESTIONE_TURNI_SERVER", "nonce", "nonce", "127.0.0.1"));
    }
    @Test public void simultaneousServersUseSameNumericOrderAsDesktop() {
        assertEquals("http://192.168.1.2:8080/", DiscoveryRules.first(Arrays.asList("192.168.1.10", "192.168.1.2")));
    }
    @Test public void replacementServerCanHaveDifferentAddress() {
        assertEquals("http://192.168.1.25:8080/", DiscoveryRules.first(Arrays.asList("192.168.1.25")));
        assertNull(DiscoveryRules.first(Arrays.asList("https://example.com", "")));
    }
}
