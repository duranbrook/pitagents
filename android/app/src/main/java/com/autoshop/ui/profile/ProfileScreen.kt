package com.autoshop.ui.profile

import android.util.Base64
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import com.autoshop.data.storage.TokenStore
import org.json.JSONObject

private fun decodeJwtPayload(token: String): JSONObject? = runCatching {
    val parts = token.split(".")
    if (parts.size < 2) return null
    val payloadBytes = Base64.decode(
        parts[1].replace('-', '+').replace('_', '/'),
        Base64.NO_WRAP or Base64.NO_PADDING,
    )
    JSONObject(String(payloadBytes, Charsets.UTF_8))
}.getOrNull()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProfileScreen(
    tokenStore: TokenStore,
    onLogout: () -> Unit,
) {
    val token = remember { tokenStore.getToken() }
    val payload = remember(token) { token?.let { decodeJwtPayload(it) } }
    val email = payload?.optString("email", null) ?: payload?.optString("sub", null) ?: "Unknown"
    val role = payload?.optString("role", null) ?: "—"

    Scaffold(
        topBar = { TopAppBar(title = { Text("Profile") }) },
    ) { innerPadding ->
        Box(
            modifier = Modifier.fillMaxSize().padding(innerPadding),
            contentAlignment = Alignment.Center,
        ) {
            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(12.dp),
                modifier = Modifier.fillMaxWidth().padding(24.dp),
            ) {
                Icon(
                    imageVector = Icons.Filled.AccountCircle,
                    contentDescription = null,
                    modifier = Modifier.size(80.dp),
                    tint = MaterialTheme.colorScheme.primary,
                )

                Spacer(modifier = Modifier.height(4.dp))

                Text(
                    text = email,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )

                Text(
                    text = "Role: $role",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Spacer(modifier = Modifier.height(16.dp))

                Button(
                    onClick = {
                        tokenStore.clearToken()
                        onLogout()
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.error,
                        contentColor = MaterialTheme.colorScheme.onError,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text("Log Out")
                }
            }
        }
    }
}
