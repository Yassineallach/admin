package com.airpointer.remote.ads

import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import android.widget.ImageView
import android.widget.TextView
import com.airpointer.remote.R
import com.google.android.gms.ads.nativead.MediaView
import com.google.android.gms.ads.nativead.NativeAd
import com.google.android.gms.ads.nativead.NativeAdView

/** Inflates [R.layout.native_ad_card] and binds a real [NativeAd] to it with every asset registered. */
object NativeAdBinder {

    fun inflate(parent: ViewGroup?, inflater: LayoutInflater, compact: Boolean = false): NativeAdView =
        inflater.inflate(if (compact) R.layout.native_ad_compact else R.layout.native_ad_card, parent, false) as NativeAdView

    fun bind(view: NativeAdView, ad: NativeAd) {
        if (view.tag === ad) return // already showing this ad: no rebinding on recomposition
        val headline = view.findViewById<TextView>(R.id.ad_headline)
        val body: TextView? = view.findViewById(R.id.ad_body)
        val advertiser = view.findViewById<TextView>(R.id.ad_advertiser)
        val icon = view.findViewById<ImageView>(R.id.ad_icon)
        val media: MediaView? = view.findViewById(R.id.ad_media)
        val cta = view.findViewById<TextView>(R.id.ad_cta)

        headline.text = ad.headline
        view.headlineView = headline

        if (body != null) {
            body.text = ad.body
            body.visibility = if (ad.body.isNullOrBlank()) View.GONE else View.VISIBLE
            view.bodyView = body
        }

        val by = ad.advertiser ?: ad.store
        advertiser.text = listOfNotNull(view.context.getString(R.string.ad_sponsored), by).joinToString(" · ")
        view.advertiserView = advertiser

        val iconDrawable = ad.icon?.drawable
        icon.setImageDrawable(iconDrawable)
        icon.visibility = if (iconDrawable == null) View.GONE else View.VISIBLE
        view.iconView = icon

        // The compact layout has no MediaView (main image/video is optional for native ads).
        if (media != null) {
            val content = ad.mediaContent
            if (content != null) {
                media.mediaContent = content
                media.setImageScaleType(ImageView.ScaleType.CENTER_CROP)
                media.visibility = View.VISIBLE
            } else media.visibility = View.GONE
            view.mediaView = media
        }

        cta.text = ad.callToAction
        cta.visibility = if (ad.callToAction.isNullOrBlank()) View.GONE else View.VISIBLE
        view.callToActionView = cta

        // Must be last: registers the views for impressions and clicks, and adds AdChoices.
        view.setNativeAd(ad)
        view.tag = ad
    }
}
