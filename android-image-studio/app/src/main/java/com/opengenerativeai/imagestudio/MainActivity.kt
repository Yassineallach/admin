package com.opengenerativeai.imagestudio

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import com.opengenerativeai.imagestudio.ui.ImageStudioTheme
import com.opengenerativeai.imagestudio.ui.StudioApp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            ImageStudioTheme {
                StudioApp()
            }
        }
    }
}
