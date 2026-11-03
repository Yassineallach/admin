package com.airpointer.remote.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleService
import androidx.lifecycle.lifecycleScope
import com.airpointer.remote.MainActivity
import com.airpointer.remote.R
import com.airpointer.remote.graph
import com.airpointer.remote.hid.BluetoothHidController
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.launch

/**
 * Foreground service (type connectedDevice) that keeps the HID registration and the host
 * connection alive while the app is in the background, and offers slide controls in the
 * notification.
 */
class AirPointerService : LifecycleService() {

    override fun onCreate() {
        super.onCreate()
        createChannel()
        try {
            ServiceCompat.startForeground(
                this, NOTIFICATION_ID, buildNotification(graph.hid.state.value),
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_CONNECTED_DEVICE else 0,
            )
        } catch (e: Exception) {
            graph.log.e("Service", "startForeground failed: ${e.message}")
            stopSelf()
            return
        }
        graph.hid.start()
        lifecycleScope.launch {
            graph.hid.state
                .map { Triple(it.phase, it.host?.name, it.support) }
                .distinctUntilChanged()
                .collect {
                    val nm = getSystemService(NotificationManager::class.java)
                    nm.notify(NOTIFICATION_ID, buildNotification(graph.hid.state.value))
                }
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        when (intent?.action) {
            ACTION_NEXT -> graph.presenter.nextSlide()
            ACTION_PREVIOUS -> graph.presenter.previousSlide()
            ACTION_STOP -> {
                graph.hid.disconnect()
                stopSelf()
            }
        }
        return START_STICKY
    }

    override fun onDestroy() {
        graph.hid.stop()
        super.onDestroy()
    }

    private fun createChannel() {
        val nm = getSystemService(NotificationManager::class.java)
        nm.createNotificationChannel(
            NotificationChannel(CHANNEL_ID, "Connection", NotificationManager.IMPORTANCE_LOW).apply {
                description = "Shows the Bluetooth pointer connection and slide controls"
                setShowBadge(false)
            },
        )
    }

    private fun buildNotification(s: BluetoothHidController.State): Notification {
        val open = PendingIntent.getActivity(
            this, 0, Intent(this, MainActivity::class.java).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP),
            PendingIntent.FLAG_IMMUTABLE,
        )
        val text = when {
            s.support == BluetoothHidController.Support.UNSUPPORTED -> "HID mode not supported on this phone"
            s.connected -> "Connected to ${s.host?.name}"
            s.phase == BluetoothHidController.Phase.CONNECTING -> "Connecting to ${s.host?.name ?: "computer"}…"
            s.reconnectAttempt > 0 -> "Reconnecting (attempt ${s.reconnectAttempt})…"
            s.registered -> "Ready — waiting for a computer"
            else -> "Starting Bluetooth HID…"
        }
        val b = NotificationCompat.Builder(this, CHANNEL_ID)
            .setSmallIcon(R.drawable.ic_stat_pointer)
            .setContentTitle("Air Pointer")
            .setContentText(text)
            .setOngoing(true)
            .setOnlyAlertOnce(true)
            .setSilent(true)
            .setContentIntent(open)
            .setCategory(NotificationCompat.CATEGORY_SERVICE)
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
        if (s.connected) {
            b.addAction(0, "Previous", action(ACTION_PREVIOUS, 1))
            b.addAction(0, "Next", action(ACTION_NEXT, 2))
        }
        b.addAction(0, "Stop", action(ACTION_STOP, 3))
        return b.build()
    }

    private fun action(a: String, code: Int) = PendingIntent.getService(
        this, code, Intent(this, AirPointerService::class.java).setAction(a), PendingIntent.FLAG_IMMUTABLE,
    )

    companion object {
        private const val CHANNEL_ID = "connection"
        private const val NOTIFICATION_ID = 1
        const val ACTION_NEXT = "com.airpointer.remote.NEXT"
        const val ACTION_PREVIOUS = "com.airpointer.remote.PREVIOUS"
        const val ACTION_STOP = "com.airpointer.remote.STOP"

        fun start(context: Context) {
            try {
                ContextCompat.startForegroundService(context, Intent(context, AirPointerService::class.java))
            } catch (e: Exception) {
                context.graph.log.e("Service", "Could not start service: ${e.message}")
            }
        }

        fun stop(context: Context) {
            context.stopService(Intent(context, AirPointerService::class.java))
        }
    }
}
