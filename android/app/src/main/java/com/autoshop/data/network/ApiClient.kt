package com.autoshop.data.network

import com.autoshop.data.storage.TokenStore
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory

private const val BASE_URL = "https://backend-production-5320.up.railway.app/"

fun buildRetrofit(tokenStore: TokenStore): Retrofit {
    val logging = HttpLoggingInterceptor().apply {
        level = if (com.autoshop.BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BODY
                else HttpLoggingInterceptor.Level.NONE
    }

    val auth = Interceptor { chain ->
        val token = tokenStore.getToken()
        val request = if (token != null) {
            chain.request()
                .newBuilder()
                .addHeader("Authorization", "Bearer $token")
                .build()
        } else {
            chain.request()
        }
        val response = chain.proceed(request)
        if (response.code == 401 && token != null) {
            // Mid-session 401 — token expired or revoked. Mark expired so LoginScreen
            // can show "Session expired" instead of dropping the user on a blank login form.
            tokenStore.expireSession()
        }
        response
    }

    val client = OkHttpClient.Builder()
        .addInterceptor(auth)
        .addInterceptor(logging)
        .build()

    return Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
}
