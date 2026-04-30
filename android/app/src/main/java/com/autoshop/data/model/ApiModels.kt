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

data class ReportVehicle(
    val year: Int?,
    val make: String?,
    val model: String?,
    val trim: String?,
    val vin: String?,
)

data class ReportFinding(
    val part: String,
    val severity: String,
    val notes: String,
)

data class ReportEstimateItem(
    val part: String,
    @SerializedName("labor_hours") val laborHours: Double,
    @SerializedName("labor_rate") val laborRate: Double? = null,
    @SerializedName("labor_cost") val laborCost: Double,
    @SerializedName("parts_cost") val partsCost: Double,
    val total: Double,
)

data class EstimateItemPatch(
    val part: String,
    @SerializedName("labor_hours") val laborHours: Double,
    @SerializedName("labor_rate") val laborRate: Double,
    @SerializedName("parts_cost") val partsCost: Double,
)

data class EstimateUpdateRequest(
    val items: List<EstimateItemPatch>,
)

data class ReportDetail(
    val id: String,
    val vehicle: ReportVehicle?,
    val summary: String?,
    val findings: List<ReportFinding>,
    val estimate: List<ReportEstimateItem>,
    val total: Double,
    @SerializedName("share_token") val shareToken: String,
    @SerializedName("created_at") val createdAt: String?,
)

// ---------------------------------------------------------------------------
// AI Chat
// ---------------------------------------------------------------------------

data class ContentBlock(
    val type: String,
    val text: String? = null,
)

data class ChatMessageRequest(
    val message: String,
    @SerializedName("image_url") val imageUrl: String? = null,
)

data class TranscribeResponse(
    val transcript: String,
)

data class UploadResponse(
    @SerializedName("image_url") val imageUrl: String,
)

// Used for optimistic UI and display
data class ChatMessage(
    val role: String,
    val content: String,
    @SerializedName("created_at") val createdAt: String?,
)

data class ChatHistoryItem(
    val id: String,
    val role: String,
    val content: List<ContentBlock>,
    @SerializedName("created_at") val createdAt: String?,
) {
    val displayText: String
        get() = content.filter { it.type == "text" }.mapNotNull { it.text }.joinToString(" ")
}

data class ChatSyncResponse(
    val text: String,
)
