package com.autoshop.ui.customers

import com.autoshop.data.model.ChatHistoryItem
import com.autoshop.data.model.ChatMessageRequest
import com.autoshop.data.model.ChatSyncResponse
import com.autoshop.data.model.CreateMessageRequest
import com.autoshop.data.model.Message
import com.autoshop.data.model.Report
import com.autoshop.data.model.ReportDetail
import com.autoshop.data.model.TranscribeResponse
import com.autoshop.data.model.UploadResponse
import com.autoshop.data.network.MessagesApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.resetMain
import kotlinx.coroutines.test.runTest
import kotlinx.coroutines.test.setMain
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.ResponseBody.Companion.toResponseBody
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import retrofit2.Response

@OptIn(ExperimentalCoroutinesApi::class)
class MessagesViewModelTest {

    private val testDispatcher = StandardTestDispatcher()

    // A realistic Message returned by the server on success
    private val serverMessage = Message(
        messageId = "msg-001",
        vehicleId = "vehicle-abc",
        direction = "out",
        channel = "sms",
        body = "Hello!",
        externalId = "ext-001",
        sentAt = "2026-04-27T10:00:00Z",
        createdAt = "2026-04-27T10:00:00Z",
    )

    @Before
    fun setUp() {
        Dispatchers.setMain(testDispatcher)
    }

    @After
    fun tearDown() {
        Dispatchers.resetMain()
    }

    // ---------------------------------------------------------------------------
    // Test 1: sendMessage inserts an optimistic placeholder immediately
    // ---------------------------------------------------------------------------

    @Test
    fun `sendMessage inserts optimistic placeholder before API responds`() = runTest {
        // Fake API that suspends until we let it through — we check state before advancing
        var sendMessageCalled = false
        val fakeApi = object : MessagesApi {
            override suspend fun listMessages(vehicleId: String): Response<List<Message>> =
                Response.success(emptyList())

            override suspend fun sendMessage(
                vehicleId: String,
                request: CreateMessageRequest,
            ): Response<Message> {
                sendMessageCalled = true
                return Response.success(serverMessage)
            }

            override suspend fun listReports(vehicleId: String): Response<List<Report>> =
                throw UnsupportedOperationException()
            override suspend fun getReport(reportId: String): Response<ReportDetail> =
                throw UnsupportedOperationException()
            override suspend fun getChatHistory(agentId: String): Response<List<ChatHistoryItem>> =
                throw UnsupportedOperationException()
            override suspend fun sendChatMessage(agentId: String, request: ChatMessageRequest): Response<ChatSyncResponse> =
                throw UnsupportedOperationException()
            override suspend fun transcribeAudio(audio: RequestBody): Response<TranscribeResponse> =
                throw UnsupportedOperationException()
            override suspend fun uploadImage(file: MultipartBody.Part): Response<UploadResponse> =
                throw UnsupportedOperationException()
        }

        val vm = MessagesViewModel(vehicleId = "vehicle-abc", api = fakeApi)
        // Let loadMessages() complete so the list starts empty
        advanceUntilIdle()

        // Sanity: no messages yet
        assertEquals(0, vm.messages.value.size)

        // Call sendMessage — placeholder is inserted synchronously
        vm.sendMessage("sms", "Hello!")

        // Before advancing coroutines, the placeholder must already be in the list
        val messagesAfterCall = vm.messages.value
        assertEquals(1, messagesAfterCall.size)
        val placeholder = messagesAfterCall.first()
        assertTrue("Placeholder id should start with 'pending-'", placeholder.messageId.startsWith("pending-"))
        assertEquals("Hello!", placeholder.body)
        assertEquals("sms", placeholder.channel)
        assertEquals("out", placeholder.direction)
    }

    // ---------------------------------------------------------------------------
    // Test 2: sendMessage replaces placeholder with real message on API success
    // ---------------------------------------------------------------------------

    @Test
    fun `sendMessage replaces placeholder with real message on API success`() = runTest {
        val fakeApi = object : MessagesApi {
            override suspend fun listMessages(vehicleId: String): Response<List<Message>> =
                Response.success(emptyList())

            override suspend fun sendMessage(
                vehicleId: String,
                request: CreateMessageRequest,
            ): Response<Message> = Response.success(serverMessage)

            override suspend fun listReports(vehicleId: String): Response<List<Report>> =
                throw UnsupportedOperationException()
            override suspend fun getReport(reportId: String): Response<ReportDetail> =
                throw UnsupportedOperationException()
            override suspend fun getChatHistory(agentId: String): Response<List<ChatHistoryItem>> =
                throw UnsupportedOperationException()
            override suspend fun sendChatMessage(agentId: String, request: ChatMessageRequest): Response<ChatSyncResponse> =
                throw UnsupportedOperationException()
            override suspend fun transcribeAudio(audio: RequestBody): Response<TranscribeResponse> =
                throw UnsupportedOperationException()
            override suspend fun uploadImage(file: MultipartBody.Part): Response<UploadResponse> =
                throw UnsupportedOperationException()
        }

        val vm = MessagesViewModel(vehicleId = "vehicle-abc", api = fakeApi)
        advanceUntilIdle()

        vm.sendMessage("sms", "Hello!")
        // Advance until the coroutine in sendMessage finishes
        advanceUntilIdle()

        val messages = vm.messages.value
        assertEquals(1, messages.size)
        val real = messages.first()
        assertEquals("msg-001", real.messageId)
        assertEquals("Hello!", real.body)
        assertNull(vm.errorMessage.value)
    }

    // ---------------------------------------------------------------------------
    // Test 3: sendMessage removes placeholder and sets errorMessage on API failure
    // ---------------------------------------------------------------------------

    @Test
    fun `sendMessage removes placeholder and sets errorMessage on API failure`() = runTest {
        val fakeApi = object : MessagesApi {
            override suspend fun listMessages(vehicleId: String): Response<List<Message>> =
                Response.success(emptyList())

            override suspend fun sendMessage(
                vehicleId: String,
                request: CreateMessageRequest,
            ): Response<Message> {
                val errorBody = "Internal Server Error".toResponseBody("text/plain".toMediaType())
                return Response.error(500, errorBody)
            }

            override suspend fun listReports(vehicleId: String): Response<List<Report>> =
                throw UnsupportedOperationException()
            override suspend fun getReport(reportId: String): Response<ReportDetail> =
                throw UnsupportedOperationException()
            override suspend fun getChatHistory(agentId: String): Response<List<ChatHistoryItem>> =
                throw UnsupportedOperationException()
            override suspend fun sendChatMessage(agentId: String, request: ChatMessageRequest): Response<ChatSyncResponse> =
                throw UnsupportedOperationException()
            override suspend fun transcribeAudio(audio: RequestBody): Response<TranscribeResponse> =
                throw UnsupportedOperationException()
            override suspend fun uploadImage(file: MultipartBody.Part): Response<UploadResponse> =
                throw UnsupportedOperationException()
        }

        val vm = MessagesViewModel(vehicleId = "vehicle-abc", api = fakeApi)
        advanceUntilIdle()

        vm.sendMessage("sms", "Hello!")
        advanceUntilIdle()

        // Placeholder should be gone
        assertEquals(0, vm.messages.value.size)
        // Error message should be set
        val error = vm.errorMessage.value
        assertTrue("errorMessage should be non-null after failure", error != null)
        assertTrue("errorMessage should mention HTTP 500", error!!.contains("500"))
    }

    // ---------------------------------------------------------------------------
    // Test 4: sendMessage with blank body does nothing
    // ---------------------------------------------------------------------------

    @Test
    fun `sendMessage with blank body does nothing`() = runTest {
        var sendMessageCalled = false
        val fakeApi = object : MessagesApi {
            override suspend fun listMessages(vehicleId: String): Response<List<Message>> =
                Response.success(emptyList())

            override suspend fun sendMessage(
                vehicleId: String,
                request: CreateMessageRequest,
            ): Response<Message> {
                sendMessageCalled = true
                return Response.success(serverMessage)
            }

            override suspend fun listReports(vehicleId: String): Response<List<Report>> =
                throw UnsupportedOperationException()
            override suspend fun getReport(reportId: String): Response<ReportDetail> =
                throw UnsupportedOperationException()
            override suspend fun getChatHistory(agentId: String): Response<List<ChatHistoryItem>> =
                throw UnsupportedOperationException()
            override suspend fun sendChatMessage(agentId: String, request: ChatMessageRequest): Response<ChatSyncResponse> =
                throw UnsupportedOperationException()
            override suspend fun transcribeAudio(audio: RequestBody): Response<TranscribeResponse> =
                throw UnsupportedOperationException()
            override suspend fun uploadImage(file: MultipartBody.Part): Response<UploadResponse> =
                throw UnsupportedOperationException()
        }

        val vm = MessagesViewModel(vehicleId = "vehicle-abc", api = fakeApi)
        advanceUntilIdle()

        // Try blank body variations
        vm.sendMessage("sms", "")
        vm.sendMessage("sms", "   ")
        vm.sendMessage("sms", "\t\n")
        advanceUntilIdle()

        // No placeholder, no API call, no error
        assertEquals(0, vm.messages.value.size)
        assertNull(vm.errorMessage.value)
        assertEquals(false, sendMessageCalled)
    }
}
