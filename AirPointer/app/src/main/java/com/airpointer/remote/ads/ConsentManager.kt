package com.airpointer.remote.ads

import android.app.Activity
import android.content.Context
import com.airpointer.remote.BuildConfig
import com.airpointer.remote.diagnostics.DiagnosticsLog
import com.google.android.ump.ConsentDebugSettings
import com.google.android.ump.ConsentInformation
import com.google.android.ump.ConsentRequestParameters
import com.google.android.ump.UserMessagingPlatform
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.concurrent.atomic.AtomicBoolean

/**
 * Google User Messaging Platform flow, as Google specifies it for AdMob:
 *  1. on every app start, update consent info (requestConsentInfoUpdate);
 *  2. show the consent form if one is required for this user/region (loadAndShowConsentFormIfRequired);
 *  3. start the Mobile Ads SDK only once canRequestAds() is true — and immediately on later starts
 *     when consent from a previous session already allows it;
 *  4. offer a "Privacy options" entry point whenever UMP reports it as REQUIRED.
 * Remote-control features never wait for this: only ads depend on it.
 */
class ConsentManager(context: Context, private val ads: AdsManager, private val log: DiagnosticsLog) {

    private val info: ConsentInformation? = runCatching { UserMessagingPlatform.getConsentInformation(context.applicationContext) }
        .onFailure { log.w(TAG, "UMP unavailable: ${it.message}") }.getOrNull()

    private val _privacyOptionsRequired = MutableStateFlow(false)
    val privacyOptionsRequired: StateFlow<Boolean> = _privacyOptionsRequired

    private val gathering = AtomicBoolean(false)

    fun gather(activity: Activity) {
        val info = info ?: return
        if (!gathering.compareAndSet(false, true)) return
        val params = ConsentRequestParameters.Builder()
            .setTagForUnderAgeOfConsent(false)
            .apply {
                if (BuildConfig.DEBUG && BuildConfig.UMP_TEST_DEVICE.isNotEmpty()) setConsentDebugSettings(
                    ConsentDebugSettings.Builder(activity)
                        .setDebugGeography(ConsentDebugSettings.DebugGeography.DEBUG_GEOGRAPHY_EEA)
                        .addTestDeviceHashedId(BuildConfig.UMP_TEST_DEVICE)
                        .build(),
                )
            }
            .build()
        try {
            info.requestConsentInfoUpdate(activity, params, {
                UserMessagingPlatform.loadAndShowConsentFormIfRequired(activity) { error ->
                    error?.let { log.w(TAG, "Consent form: ${it.errorCode} ${it.message}") }
                    onConsentResolved(info)
                }
            }, { error ->
                log.w(TAG, "Consent info update failed: ${error.errorCode} ${error.message}")
                onConsentResolved(info)
            })
        } catch (e: Throwable) {
            log.w(TAG, "Consent flow unavailable: ${e.message}")
            gathering.set(false)
        }
        // Consent obtained in an earlier session: start ads now instead of waiting for the network.
        if (info.canRequestAds()) ads.start()
    }

    private fun onConsentResolved(info: ConsentInformation) {
        gathering.set(false)
        _privacyOptionsRequired.value =
            info.privacyOptionsRequirementStatus == ConsentInformation.PrivacyOptionsRequirementStatus.REQUIRED
        if (info.canRequestAds()) ads.start() else ads.stop()
    }

    /** "Privacy options" entry point (shown only when UMP requires it). */
    fun showPrivacyOptions(activity: Activity) {
        val info = info ?: return
        UserMessagingPlatform.showPrivacyOptionsForm(activity) { error ->
            error?.let { log.w(TAG, "Privacy options: ${it.errorCode} ${it.message}") }
            onConsentResolved(info)
        }
    }

    companion object { private const val TAG = "Consent" }
}
