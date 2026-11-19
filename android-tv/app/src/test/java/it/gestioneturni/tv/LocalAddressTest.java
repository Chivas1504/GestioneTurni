package it.gestioneturni.tv;

import org.junit.Test;
import static org.junit.Assert.*;

public class LocalAddressTest {
    @Test public void acceptsPrivateDisplayEndpoints() {
        assertEquals("http://192.168.1.10:8080/", LocalAddress.normalise("192.168.1.10"));
        assertEquals("http://10.0.2.2:8080/", LocalAddress.normalise("http://10.0.2.2:8080/"));
        assertNotNull(LocalAddress.normalise("172.16.0.1"));
    }
    @Test public void rejectsExternalInvalidOrExecutableAddresses() {
        for (String value : new String[]{"google.com", "8.8.8.8", "192.168.1.999", "192.168.1.1:80",
            "javascript:alert(1)", "file:///etc/passwd", "http://u:p@192.168.1.1", "192.168.1.1/evil", "172.32.0.1"}) {
            assertNull(value, LocalAddress.normalise(value));
        }
    }
    @Test public void resourcesAreRestrictedToLocalDisplayPort() {
        assertTrue(LocalAddress.permittedResource("http://192.168.1.10:8080/api/state?t=1"));
        assertFalse(LocalAddress.permittedResource("https://example.com"));
        assertFalse(LocalAddress.permittedResource("http://192.168.1.10:80/"));
    }
}
