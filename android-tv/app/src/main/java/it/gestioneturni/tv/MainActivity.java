package it.gestioneturni.tv;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.KeyEvent;
import android.view.View;
import android.view.WindowManager;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebResourceResponse;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.CheckBox;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.io.ByteArrayInputStream;

public class MainActivity extends Activity {
    private final Handler handler = new Handler(Looper.getMainLooper());
    private WebView web;
    private TextView status;
    private SharedPreferences preferences;
    private String primary = "", backup = "";
    private boolean resumed, pageReady;
    private int failures;
    private boolean automatic = true, connecting;
    private int generation;
    private String activeUrl = "", lastServer = "";
    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private final Runnable monitor = () -> checkConnection();
    private final Runnable retry = () -> loadDisplay();
    private final Runnable loadTimeout = () -> {
        if (web != null) web.stopLoading();
        failed();
    };

    @Override public void onCreate(Bundle saved) {
        super.onCreate(saved);
        preferences = getSharedPreferences("display", MODE_PRIVATE);
        primary = preferences.getString("primary", "");
        backup = preferences.getString("backup", "");
        automatic = preferences.getBoolean("automatic", true);
        lastServer = preferences.getString("last_server", "");
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.rgb(11, 45, 71));
        LinearLayout bar = new LinearLayout(this);
        bar.setPadding(16, 0, 16, 0);
        status = new TextView(this);
        status.setTextColor(Color.WHITE);
        status.setTextSize(14);
        status.setText("Gestione Turni TV · protezione schermo attiva nell'app");
        bar.addView(status, new LinearLayout.LayoutParams(0, 48, 1));
        Button settings = new Button(this);
        settings.setText("Impostazioni");
        settings.setOnClickListener(v -> showSettings());
        bar.addView(settings);
        root.addView(bar);
        try { web = new WebView(this); }
        catch (RuntimeException error) {
            status.setText("Android System WebView non disponibile. Aggiornalo sulla TV e riapri l'app.");
            setContentView(root);
            return;
        }
        WebSettings config = web.getSettings();
        config.setJavaScriptEnabled(true);
        config.setDomStorageEnabled(true);
        config.setAllowFileAccess(false);
        config.setAllowContentAccess(false);
        config.setJavaScriptCanOpenWindowsAutomatically(false);
        config.setSupportMultipleWindows(false);
        config.setMediaPlaybackRequiresUserGesture(false);
        config.setCacheMode(WebSettings.LOAD_NO_CACHE);
        config.setUserAgentString(config.getUserAgentString() + " GestioneTurniTV/1.1");
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !LocalAddress.permittedResource(request.getUrl().toString());
            }
            @Override public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
                if (LocalAddress.permittedResource(request.getUrl().toString())) return null;
                return new WebResourceResponse("text/plain", "UTF-8", 403, "Blocked", null,
                    new ByteArrayInputStream(new byte[0]));
            }
            @Override public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame()) failed();
            }
            @Override public void onReceivedHttpError(WebView view, WebResourceRequest request, WebResourceResponse response) {
                if (request.isForMainFrame()) failed();
            }
            @Override public void onPageFinished(WebView view, String url) {
                if (!pageReady) return;
                handler.removeCallbacks(loadTimeout);
                handler.removeCallbacks(retry);
                failures = 0;
                status.setText("Gestione Turni TV · schermo mantenuto acceso · MENU o Indietro: opzioni");
            }
        });
        root.addView(web, new LinearLayout.LayoutParams(-1, 0, 1));
        setContentView(root);

    }

    private void immersive() {
        getWindow().getDecorView().setSystemUiVisibility(View.SYSTEM_UI_FLAG_FULLSCREEN
            | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            | View.SYSTEM_UI_FLAG_LAYOUT_STABLE);
    }
    @Override protected void onResume() {
        super.onResume();
        resumed = true;
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        immersive();
        if (web != null) { web.onResume(); web.setKeepScreenOn(true); loadDisplay(); }
    }
    @Override protected void onPause() {
        resumed = false;
        generation++;
        connecting = false;
        handler.removeCallbacksAndMessages(null);
        getWindow().clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        if (web != null) { web.setKeepScreenOn(false); web.onPause(); }
        super.onPause();
    }
    @Override protected void onDestroy() {
        handler.removeCallbacksAndMessages(null);
        network.shutdownNow();
        if (web != null) web.destroy();
        super.onDestroy();
    }
    private void failed() {
        if (!resumed) return;
        handler.removeCallbacks(loadTimeout);
        handler.removeCallbacks(monitor);
        pageReady = false;
        failures++;
        handler.post(() -> status.setText("PC non raggiungibile · nuovo tentativo automatico tra 5 secondi"));
        handler.removeCallbacks(retry);
        if (resumed) handler.postDelayed(retry, 5000);
    }
    private void loadDisplay() {
        if (!resumed || web == null || connecting) return;
        handler.removeCallbacks(retry);
        handler.removeCallbacks(monitor);
        handler.removeCallbacks(loadTimeout);
        connecting = true;
        int token = ++generation;
        final boolean auto = automatic;
        final String first = primary, second = backup, last = lastServer;
        status.setText(auto ? "Ricerca automatica del PC dello studio..." : "Connessione al PC...");
        network.execute(() -> {
            final String selected = DiscoveryRules.resolve(auto, ServerDiscovery::discover,
                ServerDiscovery::reachable, last, first, second);
            handler.post(() -> {
                if (!resumed || token != generation) return;
                connecting = false;
                if (selected == null) {
                    status.setText("Nessun PC disponibile. Apri Gestione Turni sul PC: riprovo automaticamente.");
                    handler.postDelayed(retry, 5000);
                    return;
                }
                activeUrl = selected;
                lastServer = selected;
                preferences.edit().putString("last_server", selected).apply();
                pageReady = true;
                status.setText("Collegamento al display dello studio...");
                web.loadUrl(selected);
                handler.removeCallbacks(loadTimeout);
                handler.postDelayed(loadTimeout, 12000);
                handler.postDelayed(monitor, 5000);
            });
        });
    }
    private void checkConnection() {
        if (!resumed || connecting || activeUrl.isEmpty()) return;
        final int token = generation;
        final String address = activeUrl;
        network.execute(() -> {
            boolean alive = ServerDiscovery.reachable(address);
            handler.post(() -> {
                if (!resumed || token != generation) return;
                if (alive) handler.postDelayed(monitor, 5000);
                else { pageReady = false; loadDisplay(); }
            });
        });
    }
    private void showSettings() {
        LinearLayout form = new LinearLayout(this);
        form.setOrientation(LinearLayout.VERTICAL);
        form.setPadding(32, 16, 32, 16);
        TextView help = new TextView(this);
        help.setText("Il collegamento automatico non richiede indirizzi.\n"
            + "Gli indirizzi manuali sono facoltativi. TV e PC devono essere sulla stessa rete.");
        form.addView(help);
        CheckBox auto = new CheckBox(this);
        auto.setText("Trova automaticamente il PC dello studio");
        auto.setChecked(automatic);
        form.addView(auto);
        EditText first = new EditText(this);
        first.setSingleLine(true);
        first.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        first.setHint("Indirizzo del primo PC");
        first.setText(primary);
        form.addView(first);
        EditText second = new EditText(this);
        second.setSingleLine(true);
        second.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        second.setHint("Secondo PC (facoltativo)");
        second.setText(backup);
        form.addView(second);
        AlertDialog dialog = new AlertDialog.Builder(this).setTitle("Collegamento allo studio")
            .setView(form).setPositiveButton("Salva e apri", null).setNegativeButton("Annulla", null).create();
        dialog.setOnShowListener(ignored -> dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener(v -> {
            String next = first.getText().toString().trim().isEmpty() && auto.isChecked() ? "" : LocalAddress.normalise(first.getText().toString());
            String other = second.getText().toString().trim().isEmpty() ? "" : LocalAddress.normalise(second.getText().toString());
            if (next == null) { first.setError("Inserisci un indirizzo IPv4 locale valido (porta 8080)"); return; }
            if (other == null) { second.setError("Indirizzo non valido"); return; }
            generation++; connecting = false;
            automatic = auto.isChecked(); primary = next; backup = other;
            preferences.edit().putString("primary", primary).putString("backup", backup).putBoolean("automatic", automatic).apply();
            failures = 0;
            dialog.dismiss();
            loadDisplay();
            if (web != null) web.requestFocus();
        }));
        dialog.show();
    }
    private void options() {
        new AlertDialog.Builder(this).setTitle("Gestione Turni TV")
            .setItems(new String[]{"Collegamento automatico / indirizzi", "Ricarica display", "Esci"}, (dialog, which) -> {
                if (which == 0) showSettings();
                else if (which == 1) { failures = 0; loadDisplay(); }
                else finish();
            }).setNegativeButton("Torna al display", null).show();
    }
    @Override public boolean onKeyDown(int key, KeyEvent event) {
        if (key == KeyEvent.KEYCODE_MENU && event.getRepeatCount() == 0) { options(); return true; }
        return super.onKeyDown(key, event);
    }
    @Override public void onBackPressed() { options(); }
}
