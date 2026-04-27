package com.autoshop.ui.customers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.autoshop.data.model.CreateMessageRequest
import com.autoshop.data.model.Message
import com.autoshop.data.network.MessagesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class MessagesViewModel(
    private val vehicleId: String,
    private val api: MessagesApi,
) : ViewModel() {

    private val _messages = MutableStateFlow<List<Message>>(emptyList())
    val messages: StateFlow<List<Message>> = _messages.asStateFlow()

    private val _isLoading = MutableStateFlow(true)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()

    private val _isSending = MutableStateFlow(false)
    val isSending: StateFlow<Boolean> = _isSending.asStateFlow()

    private val _errorMessage = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    init { loadMessages() }

    fun loadMessages() {
        viewModelScope.launch {
            _isLoading.value = true
            _errorMessage.value = null
            try {
                val response = api.listMessages(vehicleId)
                if (response.isSuccessful) {
                    _messages.value = response.body() ?: emptyList()
                } else {
                    _errorMessage.value = "Failed to load messages (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                _errorMessage.value = "Network error: ${e.message}"
            } finally {
                _isLoading.value = false
            }
        }
    }

    fun sendMessage(channel: String, body: String) {
        if (body.isBlank()) return
        val trimmed = body.trim()
        val placeholder = Message(
            messageId = "pending-${System.currentTimeMillis()}",
            vehicleId = vehicleId,
            direction = "out",
            channel = channel,
            body = trimmed,
            externalId = null,
            sentAt = null,
            createdAt = "",
        )
        _messages.value = _messages.value + placeholder

        viewModelScope.launch {
            _isSending.value = true
            try {
                val response = api.sendMessage(vehicleId, CreateMessageRequest(body = trimmed, channel = channel))
                if (response.isSuccessful) {
                    val real = response.body()!!
                    _messages.value = _messages.value.map {
                        if (it.messageId == placeholder.messageId) real else it
                    }
                } else {
                    _messages.value = _messages.value.filter { it.messageId != placeholder.messageId }
                    _errorMessage.value = "Send failed (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                _messages.value = _messages.value.filter { it.messageId != placeholder.messageId }
                _errorMessage.value = "Send failed: ${e.message}"
            } finally {
                _isSending.value = false
            }
        }
    }

    fun clearError() { _errorMessage.value = null }

    companion object {
        fun factory(vehicleId: String, api: MessagesApi): ViewModelProvider.Factory =
            object : ViewModelProvider.Factory {
                override fun <T : ViewModel> create(modelClass: Class<T>): T {
                    @Suppress("UNCHECKED_CAST")
                    return MessagesViewModel(vehicleId, api) as T
                }
            }
    }
}
