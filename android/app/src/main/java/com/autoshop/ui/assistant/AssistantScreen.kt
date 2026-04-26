package com.autoshop.ui.assistant

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.BitmapFactory
import android.media.MediaRecorder
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Image
import androidx.compose.material.icons.filled.Mic
import androidx.compose.material.icons.filled.Stop
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SegmentedButton
import androidx.compose.material3.SegmentedButtonDefaults
import androidx.compose.material3.SingleChoiceSegmentedButtonRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalSoftwareKeyboardController
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.core.content.ContextCompat
import com.autoshop.data.model.ChatHistoryItem
import com.autoshop.data.model.ChatMessage
import com.autoshop.data.model.ChatMessageRequest
import com.autoshop.data.network.MessagesApi
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

private data class Agent(val id: String, val name: String)
private val AGENTS = listOf(Agent("assistant", "Assistant"), Agent("tom", "Tom"))

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AssistantScreen(messagesApi: MessagesApi) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val listState = rememberLazyListState()
    val keyboardController = LocalSoftwareKeyboardController.current

    // Agent
    var selectedIndex by remember { mutableIntStateOf(0) }
    val agentId = AGENTS[selectedIndex].id

    // Chat
    var messages by remember { mutableStateOf<List<ChatMessage>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var isSending by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var inputText by remember { mutableStateOf("") }

    // Voice
    var isRecording by remember { mutableStateOf(false) }
    var isTranscribing by remember { mutableStateOf(false) }
    var pendingRecording by remember { mutableStateOf(false) }

    // Use a holder to avoid triggering recomposition when MediaRecorder changes
    class RecorderHolder { var recorder: MediaRecorder? = null; var file: File? = null }
    val recorderHolder = remember { RecorderHolder() }

    // Photo
    var photoUri by remember { mutableStateOf<Uri?>(null) }
    var uploadedImageUrl by remember { mutableStateOf<String?>(null) }
    var isUploading by remember { mutableStateOf(false) }
    var thumbnail by remember { mutableStateOf<ImageBitmap?>(null) }

    // Recording pulse animation
    val infiniteTransition = rememberInfiniteTransition(label = "rec")
    val micAlpha by infiniteTransition.animateFloat(
        initialValue = 1f,
        targetValue = 0.25f,
        animationSpec = infiniteRepeatable(tween(500), RepeatMode.Reverse),
        label = "mic_alpha",
    )

    // Mic permission
    val micPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted -> if (granted) pendingRecording = true }

    // Photo picker
    val photoPickerLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.PickVisualMedia()
    ) { uri -> if (uri != null) photoUri = uri }

    // Auto-start recording after permission granted
    LaunchedEffect(pendingRecording) {
        if (!pendingRecording) return@LaunchedEffect
        pendingRecording = false
        val file = withContext(Dispatchers.IO) {
            File.createTempFile("voice_", ".m4a", context.cacheDir)
        }
        recorderHolder.file = file
        val rec = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) MediaRecorder(context)
                  else @Suppress("DEPRECATION") MediaRecorder()
        rec.setAudioSource(MediaRecorder.AudioSource.MIC)
        rec.setOutputFormat(MediaRecorder.OutputFormat.MPEG_4)
        rec.setAudioEncoder(MediaRecorder.AudioEncoder.AAC)
        rec.setAudioSamplingRate(16000)
        rec.setAudioChannels(1)
        rec.setAudioEncodingBitRate(64000)
        rec.setOutputFile(file.absolutePath)
        withContext(Dispatchers.IO) { rec.prepare() }
        rec.start()
        recorderHolder.recorder = rec
        isRecording = true
    }

    // Thumbnail loading
    LaunchedEffect(photoUri) {
        thumbnail = null
        val uri = photoUri ?: return@LaunchedEffect
        thumbnail = withContext(Dispatchers.IO) {
            runCatching {
                val opts = BitmapFactory.Options().apply { inSampleSize = 4 }
                context.contentResolver.openInputStream(uri)?.use { stream ->
                    BitmapFactory.decodeStream(stream, null, opts)?.asImageBitmap()
                }
            }.getOrNull()
        }
    }

    // Auto-upload when photo selected
    LaunchedEffect(photoUri) {
        uploadedImageUrl = null
        val uri = photoUri ?: return@LaunchedEffect
        isUploading = true
        try {
            val mimeType = context.contentResolver.getType(uri) ?: "image/jpeg"
            val bytes = withContext(Dispatchers.IO) {
                context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
            } ?: run { errorMessage = "Could not read image."; photoUri = null; return@LaunchedEffect }
            val ext = when (mimeType) { "image/png" -> "png"; "image/webp" -> "webp"; else -> "jpg" }
            val part = MultipartBody.Part.createFormData(
                "file", "photo.$ext", bytes.toRequestBody(mimeType.toMediaType()),
            )
            val response = messagesApi.uploadImage(part)
            if (response.isSuccessful) {
                uploadedImageUrl = response.body()?.imageUrl
            } else {
                errorMessage = "Upload failed (HTTP ${response.code()})."
                photoUri = null
            }
        } catch (e: Exception) {
            errorMessage = "Upload error: ${e.message}"
            photoUri = null
        } finally {
            isUploading = false
        }
    }

    // Release recorder if screen leaves composition
    DisposableEffect(Unit) {
        onDispose {
            runCatching { recorderHolder.recorder?.stop() }
            runCatching { recorderHolder.recorder?.release() }
        }
    }

    fun scrollToBottom() {
        if (messages.isNotEmpty()) scope.launch { listState.animateScrollToItem(messages.size - 1) }
    }

    fun loadHistory() {
        scope.launch {
            isLoading = true
            errorMessage = null
            messages = emptyList()
            try {
                val response = messagesApi.getChatHistory(agentId)
                if (response.isSuccessful) {
                    messages = response.body()?.map { item ->
                        ChatMessage(role = item.role, content = item.displayText, createdAt = item.createdAt)
                    } ?: emptyList()
                    scrollToBottom()
                } else {
                    errorMessage = "Failed to load history (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                errorMessage = "Network error: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    fun stopAndTranscribe() {
        isRecording = false
        runCatching { recorderHolder.recorder?.stop() }
        runCatching { recorderHolder.recorder?.release() }
        recorderHolder.recorder = null
        val file = recorderHolder.file ?: return
        recorderHolder.file = null
        scope.launch {
            isTranscribing = true
            try {
                val bytes = withContext(Dispatchers.IO) { file.readBytes() }
                val response = messagesApi.transcribeAudio(bytes.toRequestBody("audio/mp4".toMediaType()))
                if (response.isSuccessful) {
                    val transcript = response.body()?.transcript.orEmpty()
                    if (transcript.isNotBlank()) {
                        inputText = if (inputText.isBlank()) transcript else "${inputText.trimEnd()} $transcript"
                    }
                } else {
                    errorMessage = "Transcription failed (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                errorMessage = "Transcription error: ${e.message}"
            } finally {
                isTranscribing = false
                withContext(Dispatchers.IO) { runCatching { file.delete() } }
            }
        }
    }

    fun sendMessage() {
        if ((inputText.isBlank() && uploadedImageUrl == null) || isSending) return
        val content = inputText.trim()
        val imageUrl = uploadedImageUrl
        inputText = ""
        uploadedImageUrl = null
        photoUri = null
        thumbnail = null
        keyboardController?.hide()
        scope.launch {
            isSending = true
            val displayText = content.ifBlank { "📷" }
            messages = messages + ChatMessage(role = "user", content = displayText, createdAt = null)
            scrollToBottom()
            try {
                val response = messagesApi.sendChatMessage(agentId, ChatMessageRequest(message = content, imageUrl = imageUrl))
                if (response.isSuccessful) {
                    response.body()?.let { reply ->
                        messages = messages + ChatMessage(role = "assistant", content = reply.text, createdAt = null)
                        scrollToBottom()
                    }
                } else {
                    errorMessage = "Send failed (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                errorMessage = "Network error: ${e.message}"
            } finally {
                isSending = false
            }
        }
    }

    LaunchedEffect(agentId) { loadHistory() }

    Column(modifier = Modifier.fillMaxSize()) {

        // Agent picker
        SingleChoiceSegmentedButtonRow(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 8.dp),
        ) {
            AGENTS.forEachIndexed { index, agent ->
                SegmentedButton(
                    selected = selectedIndex == index,
                    onClick = { selectedIndex = index },
                    shape = SegmentedButtonDefaults.itemShape(index = index, count = AGENTS.size),
                    label = { Text(agent.name) },
                )
            }
        }

        // Messages
        Box(
            modifier = Modifier
                .weight(1f)
                .clickable(interactionSource = remember { MutableInteractionSource() }, indication = null) {
                    keyboardController?.hide()
                },
        ) {
            when {
                isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                errorMessage != null -> Text(
                    text = errorMessage!!,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.align(Alignment.Center).padding(16.dp),
                )
                messages.isEmpty() -> Text(
                    text = "Say hello to ${AGENTS[selectedIndex].name}.",
                    modifier = Modifier.align(Alignment.Center).padding(16.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp, vertical = 8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(messages) { ChatBubble(it) }
                }
            }
        }

        HorizontalDivider()

        // Photo preview strip
        if (photoUri != null) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(start = 12.dp, top = 6.dp),
            ) {
                Box {
                    if (isUploading || thumbnail == null) {
                        Box(
                            modifier = Modifier
                                .size(60.dp)
                                .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp)),
                            contentAlignment = Alignment.Center,
                        ) {
                            CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
                        }
                    } else {
                        Image(
                            bitmap = thumbnail!!,
                            contentDescription = "Attached photo",
                            modifier = Modifier.size(60.dp).clip(RoundedCornerShape(8.dp)),
                            contentScale = ContentScale.Crop,
                        )
                    }
                    IconButton(
                        onClick = { photoUri = null; uploadedImageUrl = null; thumbnail = null },
                        modifier = Modifier.size(22.dp).align(Alignment.TopEnd),
                    ) {
                        Icon(
                            Icons.Filled.Close,
                            contentDescription = "Remove photo",
                            modifier = Modifier.size(14.dp),
                        )
                    }
                }
            }
        }

        // Input row
        Row(
            verticalAlignment = Alignment.CenterVertically,
            modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp, vertical = 4.dp),
        ) {
            // Photo attach
            IconButton(onClick = {
                photoPickerLauncher.launch(
                    PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly)
                )
            }) {
                Icon(
                    Icons.Filled.Image,
                    contentDescription = "Attach photo",
                    tint = MaterialTheme.colorScheme.primary,
                )
            }

            OutlinedTextField(
                value = inputText,
                onValueChange = { inputText = it },
                placeholder = { Text(if (isRecording) "Recording…" else "Ask ${AGENTS[selectedIndex].name}…") },
                modifier = Modifier.weight(1f),
                maxLines = 4,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { sendMessage() }),
            )

            // Send / Mic / Stop
            val canSend = (inputText.isNotBlank() || uploadedImageUrl != null) && !isRecording
            IconButton(
                onClick = {
                    when {
                        isRecording -> stopAndTranscribe()
                        isTranscribing || isSending -> Unit
                        canSend -> sendMessage()
                        else -> {
                            val hasPerm = ContextCompat.checkSelfPermission(
                                context, Manifest.permission.RECORD_AUDIO
                            ) == PackageManager.PERMISSION_GRANTED
                            if (hasPerm) pendingRecording = true
                            else micPermissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
                        }
                    }
                },
                enabled = !isTranscribing && !isSending || isRecording,
            ) {
                when {
                    isSending || isTranscribing ->
                        CircularProgressIndicator(modifier = Modifier.size(20.dp), strokeWidth = 2.dp)
                    isRecording ->
                        Icon(
                            Icons.Filled.Stop,
                            contentDescription = "Stop recording",
                            tint = MaterialTheme.colorScheme.error.copy(alpha = micAlpha),
                            modifier = Modifier.size(28.dp),
                        )
                    canSend ->
                        Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send")
                    else ->
                        Icon(Icons.Filled.Mic, contentDescription = "Voice input")
                }
            }
        }
    }
}

@Composable
private fun ChatBubble(message: ChatMessage) {
    val isUser = message.role == "user"
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start,
    ) {
        Box(
            modifier = Modifier
                .widthIn(max = 280.dp)
                .background(
                    color = if (isUser) MaterialTheme.colorScheme.primaryContainer
                            else MaterialTheme.colorScheme.secondaryContainer,
                    shape = RoundedCornerShape(
                        topStart = 12.dp, topEnd = 12.dp,
                        bottomStart = if (isUser) 12.dp else 2.dp,
                        bottomEnd = if (isUser) 2.dp else 12.dp,
                    ),
                )
                .padding(horizontal = 12.dp, vertical = 8.dp),
        ) {
            Column {
                Text(
                    text = message.role.replaceFirstChar { it.uppercase() },
                    style = MaterialTheme.typography.labelSmall,
                    color = if (isUser) MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f)
                            else MaterialTheme.colorScheme.onSecondaryContainer.copy(alpha = 0.7f),
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = message.content,
                    style = MaterialTheme.typography.bodyMedium,
                    color = if (isUser) MaterialTheme.colorScheme.onPrimaryContainer
                            else MaterialTheme.colorScheme.onSecondaryContainer,
                )
            }
        }
    }
}
