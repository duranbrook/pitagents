package com.autoshop.data.model

import com.google.gson.annotations.SerializedName

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

data class LoginRequest(
    val email: String,
    val password: String,
)

data class LoginResponse(
    @SerializedName("access_token") val accessToken: String,
    @SerializedName("token_type") val tokenType: String,
)

// ---------------------------------------------------------------------------
// Customers
// ---------------------------------------------------------------------------

data class Customer(
    @SerializedName("customer_id") val customerId: String,
    @SerializedName("shop_id") val shopId: String,
    val name: String,
    val email: String?,
    val phone: String?,
    @SerializedName("created_at") val createdAt: String,
)

data class CreateCustomerRequest(
    val name: String,
    val email: String? = null,
    val phone: String? = null,
)

// ---------------------------------------------------------------------------
// Vehicles
// ---------------------------------------------------------------------------

data class Vehicle(
    @SerializedName("vehicle_id") val vehicleId: String,
    @SerializedName("customer_id") val customerId: String,
    val year: Int,
    val make: String,
    val model: String,
    val trim: String?,
    val vin: String?,
    val color: String?,
    @SerializedName("created_at") val createdAt: String,
)

data class CreateVehicleRequest(
    val year: Int,
    val make: String,
    val model: String,
    val trim: String? = null,
    val vin: String? = null,
    val color: String? = null,
)

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

data class Message(
    @SerializedName("message_id") val messageId: String,
    @SerializedName("vehicle_id") val vehicleId: String,
    val direction: String,
    val channel: String,
    val body: String,
    @SerializedName("external_id") val externalId: String?,
    @SerializedName("sent_at") val sentAt: String?,
    @SerializedName("created_at") val createdAt: String,
)

data class CreateMessageRequest(
    val body: String,
    val channel: String,
    val subject: String? = null,
)

// ---------------------------------------------------------------------------
// Reports
// ---------------------------------------------------------------------------

data class Report(
    @SerializedName("report_id") val reportId: String,
    val title: String?,
    val status: String,
    @SerializedName("estimate_total") val estimateTotal: Double?,
    @SerializedName("created_at") val createdAt: String,
)

// ---------------------------------------------------------------------------
// AI Chat
// ---------------------------------------------------------------------------

data class ChatMessageRequest(
    val content: String,
    @SerializedName("agent_id") val agentId: String = "assistant",
)

data class ChatMessage(
    val role: String,
    val content: String,
    @SerializedName("created_at") val createdAt: String?,
)

data class ChatMessageResponse(
    val role: String,
    val content: String,
    @SerializedName("created_at") val createdAt: String?,
)

data class ChatHistoryResponse(
    val messages: List<ChatMessage>,
)
