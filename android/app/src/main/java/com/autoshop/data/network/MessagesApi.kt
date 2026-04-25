package com.autoshop.data.network

import com.autoshop.data.model.ChatHistoryResponse
import com.autoshop.data.model.ChatMessage
import com.autoshop.data.model.ChatMessageRequest
import com.autoshop.data.model.ChatMessageResponse
import com.autoshop.data.model.CreateMessageRequest
import com.autoshop.data.model.Message
import com.autoshop.data.model.Report
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface MessagesApi {

    @GET("vehicles/{id}/messages")
    suspend fun listMessages(@Path("id") vehicleId: String): Response<List<Message>>

    @POST("vehicles/{id}/messages")
    suspend fun sendMessage(
        @Path("id") vehicleId: String,
        @Body request: CreateMessageRequest,
    ): Response<Message>

    @GET("vehicles/{id}/reports")
    suspend fun listReports(@Path("id") vehicleId: String): Response<List<Report>>

    @GET("chat/history")
    suspend fun getChatHistory(): Response<ChatHistoryResponse>

    @POST("chat/message")
    suspend fun sendChatMessage(@Body request: ChatMessageRequest): Response<ChatMessageResponse>
}
