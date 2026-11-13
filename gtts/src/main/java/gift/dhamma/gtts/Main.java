package gift.dhamma.gtts;

import android.app.Activity;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;
import android.speech.tts.Voice;
import android.util.Log;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileWriter;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

// Synthesises every line of assets/lines.tsv to files/out/<id>.wav, one after another, then writes files/out/done.txt.
// files/out/voices.txt lists what the engine offers for the language, so a run shows which voice was used and why.
public class Main extends Activity {
    static final String TAG = "GTTS";
    TextToSpeech tts;
    final List<String[]> lines = new ArrayList<>();
    File out;
    int next = 0;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        out = new File(getFilesDir(), "out");
        out.mkdirs();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(getAssets().open("lines.tsv"), "UTF-8"))) {
            for (String l; (l = r.readLine()) != null; ) {
                String[] p = l.split("\t", 2);
                if (p.length == 2 && !new File(out, p[0] + ".wav").exists()) lines.add(p);
            }
        } catch (Exception e) {
            log("error reading lines: " + e);
        }
        tts = new TextToSpeech(this, this::onInit, "com.google.android.tts");
    }

    void onInit(int status) {
        try {
            String tag = new BufferedReader(new InputStreamReader(getAssets().open("voice.txt"), "UTF-8")).readLine().trim();
            Locale want = Locale.forLanguageTag(tag);
            StringBuilder sb = new StringBuilder("init " + status + " engine " + tts.getDefaultEngine() + "\n");
            Voice pick = null;
            if (tts.getVoices() != null) for (Voice v : tts.getVoices()) {
                if (!v.getLocale().getLanguage().equals(want.getLanguage())) continue;
                sb.append(v.getName()).append(" network=").append(v.isNetworkConnectionRequired())
                  .append(" features=").append(v.getFeatures()).append(" quality=").append(v.getQuality()).append('\n');
                if (pick == null || (pick.isNetworkConnectionRequired() && !v.isNetworkConnectionRequired())) pick = v;
            }
            int lang = tts.setLanguage(want);
            sb.append("setLanguage ").append(lang).append(" pick ").append(pick == null ? "none" : pick.getName()).append('\n');
            if (pick != null) sb.append("setVoice ").append(tts.setVoice(pick)).append('\n');
            write("voices.txt", sb.toString());
            log(sb.toString());
        } catch (Exception e) {
            log("error init: " + e);
        }
        tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
            public void onStart(String id) {}
            public void onDone(String id) { speakNext(); }
            public void onError(String id) { log("error " + id); speakNext(); }
        });
        speakNext();
    }

    synchronized void speakNext() {
        if (next >= lines.size()) {
            write("done.txt", "done " + lines.size() + "\n");
            log("done");
            return;
        }
        String[] p = lines.get(next++);
        tts.synthesizeToFile(p[1], null, new File(out, p[0] + ".wav"), p[0]);
    }

    void write(String name, String text) {
        try (FileWriter w = new FileWriter(new File(out, name))) { w.write(text); } catch (Exception e) { Log.e(TAG, "write", e); }
    }

    void log(String s) { Log.i(TAG, s); }
}
