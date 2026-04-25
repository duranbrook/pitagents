package com.autoshop

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import com.autoshop.ui.nav.AppNavigation

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val app = application as AutoShopApp
        setContent {
            MaterialTheme {
                Surface {
                    AppNavigation(
                        tokenStore = app.tokenStore,
                        authApi = app.authApi,
                        customersApi = app.customersApi,
                        messagesApi = app.messagesApi,
                    )
                }
            }
        }
    }
}
