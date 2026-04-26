package com.autoshop

import android.app.Application
import com.autoshop.data.network.AuthApi
import com.autoshop.data.network.CustomersApi
import com.autoshop.data.network.MessagesApi
import com.autoshop.data.network.buildRetrofit
import com.autoshop.data.storage.TokenStore

class AutoShopApp : Application() {

    lateinit var tokenStore: TokenStore
        private set

    lateinit var authApi: AuthApi
        private set

    lateinit var customersApi: CustomersApi
        private set

    lateinit var messagesApi: MessagesApi
        private set

    var shopId: String = ""
        private set

    override fun onCreate() {
        super.onCreate()
        tokenStore = TokenStore(this)
        shopId = tokenStore.getShopId()
        val retrofit = buildRetrofit(tokenStore)
        authApi = retrofit.create(AuthApi::class.java)
        customersApi = retrofit.create(CustomersApi::class.java)
        messagesApi = retrofit.create(MessagesApi::class.java)
    }
}
