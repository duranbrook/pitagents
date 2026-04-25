package com.autoshop.data.storage

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

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

    fun saveToken(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
        _isLoggedIn.value = true
    }

    fun getToken(): String? = prefs.getString(KEY_TOKEN, null)

    fun clearToken() {
        prefs.edit().remove(KEY_TOKEN).apply()
        _isLoggedIn.value = false
    }

    companion object {
        private const val KEY_TOKEN = "jwt"
    }
}
