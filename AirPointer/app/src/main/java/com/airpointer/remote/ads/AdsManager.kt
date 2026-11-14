package com.airpointer.remote.ads

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import com.airpointer.remote.BuildConfig
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.google.android.gms.ads.AdListener
import com.google.android.gms.ads.AdLoader
import com.google.android.gms.ads.AdRequest
import com.google.android.gms.ads.LoadAdError
import com.google.android.gms.ads.MobileAds
import com.google.android.gms.ads.nativead.NativeAd
import com.google.android.gms.ads.nativead.NativeAdOptions
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

/**
 * Central native-ad manager: SDK initialisation (after consent, off the main thread), one
 * cached ad per [AdPlacement], de-duplicated requests, back-off on failure and cleanup.
 * Nothing here blocks the main thread or waits on the Bluetooth / Wi-Fi code.
 */
class AdsManager(context: Context, private val log: DiagnosticsLog) {

    private val app = context.applicationContext
    private val main = Handler(Looper.getMainLooper())
    private val cache = NativeAdCache<AdPlacement, NativeAd>(clock = SystemClock::elapsedRealtime, destroy = { it.destroy() })

    private val _ready = MutableStateFlow(false)
    /** True once consent allows ad requests and the SDK has initialised. */
    val ready: StateFlow<Boolean> = _ready

    private val _ads = MutableStateFlow<Map<AdPlacement, NativeAdCache.Slot<NativeAd>>>(emptyMap())
    val ads: StateFlow<Map<AdPlacement, NativeAdCache.Slot<NativeAd>>> = _ads

    @Volatile private var initStarted = false

    /** Call when UMP says ads may be requested. Idempotent. */
    fun start() {
        if (initStarted) return
        initStarted = true
        Thread({
            try {
                MobileAds.initialize(app) {
                    main.post {
                        _ready.value = true
                        log.i(TAG, "Mobile Ads SDK initialised${if (BuildConfig.ADMOB_TEST_IDS) " (test ads)" else ""}")
                        request(AdPlacement.HOME) // the screen users see most; others load on first visit
                    }
                }
            } catch (e: Throwable) {
                log.w(TAG, "Mobile Ads SDK unavailable: ${e.message}")
            }
        }, "ads-init").apply { isDaemon = true; start() }
    }

    /** Consent withdrawn: stop serving and free every ad. */
    fun stop() = main.post {
        _ready.value = false
        cache.clear()
        publish()
    }

    /** A screen with [placement] became visible. Loads only when needed (see [NativeAdCache]). Main thread. */
    fun request(placement: AdPlacement) {
        if (!_ready.value || !cache.shouldLoad(placement)) return
        cache.markLoading(placement)
        publish()
        val loader = AdLoader.Builder(app, unitId(placement))
            .forNativeAd { ad ->
                if (!_ready.value) { ad.destroy(); return@forNativeAd }
                cache.onLoaded(placement, ad)
                publish()
            }
            .withAdListener(object : AdListener() {
                override fun onAdFailedToLoad(error: LoadAdError) {
                    log.w(TAG, "${placement.name} native ad failed: ${error.code} ${error.message}")
                    cache.onFailed(placement, error.code)
                    publish()
                }
            })
            .withNativeAdOptions(
                NativeAdOptions.Builder()
                    .setAdChoicesPlacement(NativeAdOptions.ADCHOICES_TOP_RIGHT)
                    .setMediaAspectRatio(NativeAdOptions.NATIVE_MEDIA_ASPECT_RATIO_LANDSCAPE)
                    .build(),
            )
            .build()
        loader.loadAd(AdRequest.Builder().build())
    }

    /** The ad to show for [placement], or null (never an expired ad). Main thread. */
    fun displayable(placement: AdPlacement): NativeAd? = cache.displayable(placement)

    private fun publish() {
        _ads.value = AdPlacement.entries.associateWith { cache.slot(it) }
    }

    companion object {
        private const val TAG = "Ads"
        fun unitId(p: AdPlacement): String = when (p) {
            AdPlacement.HOME -> BuildConfig.ADMOB_NATIVE_HOME
            AdPlacement.CONNECTION -> BuildConfig.ADMOB_NATIVE_CONNECTION
            AdPlacement.SETTINGS -> BuildConfig.ADMOB_NATIVE_SETTINGS
        }
    }
}
