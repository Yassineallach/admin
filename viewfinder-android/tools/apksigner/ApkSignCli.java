import com.android.apksig.ApkSigner;
import com.android.apksig.ApkVerifier;

import java.io.File;
import java.io.FileInputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.KeyStore;
import java.security.PrivateKey;
import java.security.cert.Certificate;
import java.security.cert.X509Certificate;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * Minimal drop-in for Android build-tools' `apksigner` (sign / verify), built
 * on Google's apksig library. Lets Godot sign APKs on machines that cannot
 * download the Android SDK build-tools.
 */
public class ApkSignCli {
    static String pass(String v) throws Exception {
        if (v == null) return null;
        if (v.startsWith("pass:")) return v.substring(5);
        if (v.startsWith("env:")) return System.getenv(v.substring(4));
        if (v.startsWith("file:")) return Files.readString(new File(v.substring(5)).toPath()).trim();
        return v;
    }

    public static void main(String[] a) throws Exception {
        if (a.length == 0) {
            System.err.println("usage: apksigner sign|verify [options] app.apk");
            System.exit(2);
        }
        if (a[0].equals("--version") || a[0].equals("version")) {
            System.out.println("0.9-apksig-2.3.0");
            return;
        }
        String ks = null, ksPass = "pass:android", alias = null, keyPass = null, out = null, in = null;
        int minSdk = 24;
        for (int i = 1; i < a.length; i++) {
            String s = a[i];
            switch (s) {
                case "--ks": ks = a[++i]; break;
                case "--ks-pass": ksPass = a[++i]; break;
                case "--ks-key-alias": alias = a[++i]; break;
                case "--key-pass": keyPass = a[++i]; break;
                case "--out": out = a[++i]; break;
                case "--min-sdk-version": minSdk = Integer.parseInt(a[++i]); break;
                case "-v": case "--verbose": case "--print-certs": break;
                default:
                    if (s.startsWith("--")) {
                        if (i + 1 < a.length - 1 && !a[i + 1].startsWith("--")) i++;  // skip flag value
                    } else {
                        in = s;
                    }
            }
        }
        if (in == null) {
            System.err.println("apksigner: no APK given");
            System.exit(2);
        }
        File input = new File(in);

        if (a[0].equals("verify")) {
            ApkVerifier.Result r = new ApkVerifier.Builder(input).build().verify();
            System.out.println("Verifies: " + r.isVerified());
            System.out.println("Verified using v1 scheme (JAR signing): " + r.isVerifiedUsingV1Scheme());
            System.out.println("Verified using v2 scheme (APK Signature Scheme v2): " + r.isVerifiedUsingV2Scheme());
            for (Object e : r.getErrors()) System.out.println("ERROR: " + e);
            System.exit(r.isVerified() ? 0 : 1);
        }
        if (!a[0].equals("sign")) {
            System.err.println("apksigner: unknown command " + a[0]);
            System.exit(2);
        }

        char[] storePw = pass(ksPass).toCharArray();
        KeyStore store = KeyStore.getInstance(new File(ks), storePw);
        if (alias == null) alias = Collections.list(store.aliases()).get(0);
        char[] keyPw = keyPass != null ? pass(keyPass).toCharArray() : storePw;
        PrivateKey key = (PrivateKey) store.getKey(alias, keyPw);
        List<X509Certificate> certs = new ArrayList<>();
        for (Certificate c : store.getCertificateChain(alias)) certs.add((X509Certificate) c);

        ApkSigner.SignerConfig cfg = new ApkSigner.SignerConfig.Builder("CERT", key, certs).build();
        File output = out != null ? new File(out) : File.createTempFile("signed", ".apk", input.getAbsoluteFile().getParentFile());
        if (out == null) output.deleteOnExit();
        new ApkSigner.Builder(Collections.singletonList(cfg))
                .setInputApk(input)
                .setOutputApk(output)
                .setMinSdkVersion(Math.max(minSdk, 24))
                // v1 (JAR) signing in apksig 2.3.0 relies on JDK internals removed in
                // modern Java. APK Signature Scheme v2 alone is valid on API 24+,
                // which is Godot 4.7's minimum Android version.
                .setV1SigningEnabled(false)
                .setV2SigningEnabled(true)
                .build()
                .sign();
        if (out == null) Files.move(output.toPath(), input.toPath(), StandardCopyOption.REPLACE_EXISTING);
        System.out.println("Signed");
    }
}
