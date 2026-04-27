package com.autoshop.data.storage

import android.content.Context
import android.util.Base64
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import org.json.JSONObject

class TokenStore(context: Context) {

    private val prefs = EncryptedSharedPreferences.create(
        context,
        "autoshop_secure_prefs",
        MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
    )

    private val _isLoggedIn = MutableStateFlow(prefs.getString(KEY_TOKEN, null) != null)
    val isLoggedIn: StateFlow<Boolean> get() = _isLoggedIn

    // Set when the auth interceptor clears the token because of a 401 mid-session.
    // LoginScreen reads + clears this so the user sees "Session expired" instead of a blank screen.
    private val _sessionExpired = MutableStateFlow(false)
    val sessionExpired: StateFlow<Boolean> get() = _sessionExpired

    fun saveToken(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
        _sessionExpired.value = false
        _isLoggedIn.value = true
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun clearToken() {
        prefs.edit().remove(KEY_TOKEN).apply()
        _isLoggedIn.value = false
    }

    /** Called by the auth interceptor on a mid-session 401 (token expired/revoked). */
    fun expireSession() {
        if (prefs.getString(KEY_TOKEN, null) != null) {
            prefs.edit().remove(KEY_TOKEN).apply()
            _sessionExpired.value = true
            _isLoggedIn.value = false
        }
    }

    fun consumeSessionExpired() {
        _sessionExpired.value = false
    }

    /** Decode the JWT payload and return the `email` claim, or empty string on failure. */
    fun getEmail(): String = decodePayload()?.optString("email") ?: ""

    /** Decode the JWT payload and return the `shop_id` claim, or empty string on failure. */
    fun getShopId(): String = decodePayload()?.optString("shop_id") ?: ""

    private fun decodePayload(): JSONObject? {
        val token = getToken() ?: return null
        return try {
            val segment = token.split(".").getOrNull(1) ?: return null
            // Pad to a multiple of 4 for Base64 decoding
            val padded = segment + "=".repeat((4 - segment.length % 4) % 4)
            val bytes = Base64.decode(padded, Base64.URL_SAFE)
            JSONObject(String(bytes))
        } catch (e: Exception) {
            null
        }
    }

    companion object {
        private const val KEY_TOKEN = "jwt"
    }
}
