package com.autoshop.data.network

import com.autoshop.data.model.ChatHistoryItem
import com.autoshop.data.model.ChatMessageRequest
import com.autoshop.data.model.ChatSyncResponse
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

    @GET("chat/{agentId}/history")
    suspend fun getChatHistory(@Path("agentId") agentId: String): Response<List<ChatHistoryItem>>

    @POST("chat/{agentId}/message/sync")
    suspend fun sendChatMessage(
        @Path("agentId") agentId: String,
        @Body request: ChatMessageRequest,
    ): Response<ChatSyncResponse>
}
