package com.airpointer.remote.screenshots

import android.view.LayoutInflater
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.TextView
import androidx.activity.ComponentActivity
import com.airpointer.remote.R
import com.github.takahirom.roborazzi.captureRoboImage
import com.google.android.gms.ads.nativead.NativeAdView
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.Robolectric
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import org.robolectric.annotation.GraphicsMode

/**
 * DESIGN PREVIEW ONLY (test code): renders the production native_ad_card.xml layout — the real
 * NativeAdView class — with sample text written straight into its TextViews, to review spacing,
 * contrast and attribution. The app never creates ad content; it binds real SDK NativeAd objects.
 */
@RunWith(RobolectricTestRunner::class)
@GraphicsMode(GraphicsMode.Mode.NATIVE)
@Config(sdk = [34], qualifiers = "w411dp-h891dp-night-xxhdpi")
class AdLayoutPreview {
    @Test fun nativeAdLayout() {
        val activity = Robolectric.buildActivity(ComponentActivity::class.java).setup().get()
        val host = FrameLayout(activity).apply { setBackgroundColor(0xFF090A0D.toInt()); setPadding(60, 60, 60, 60) }
        val ad = LayoutInflater.from(activity).inflate(R.layout.native_ad_card, host, false) as NativeAdView
        ad.findViewById<TextView>(R.id.ad_advertiser).text = "Sponsored · Example Advertiser"
        ad.findViewById<TextView>(R.id.ad_headline).text = "Sample headline for layout review"
        ad.findViewById<TextView>(R.id.ad_body).text = "Sample body text, two lines at most, secondary colour on the dark card."
        ad.findViewById<ImageView>(R.id.ad_icon).setImageResource(R.drawable.ic_launcher_foreground)
        ad.findViewById<View>(R.id.ad_media).visibility = View.GONE
        ad.findViewById<TextView>(R.id.ad_cta).text = "Install"
        host.addView(ad)
        activity.setContentView(host)
        host.captureRoboImage("build/screenshots/audit/native-ad-layout.png")
    }
}
