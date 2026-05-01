package com.autoshop

import android.Manifest
import android.content.pm.PackageManager
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.view.PreviewView
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.File
import java.io.OutputStreamWriter
import java.net.HttpURLConnection
import java.net.URL
import java.util.UUID

/**
 * Main recording screen for the Technician Assistant application.
 *
 * Features:
 * - Live camera preview via CameraX [PreviewView]
 * - Bluetooth-routed audio recording via [AudioRecorder]
 * - Combined video capture via [VideoCapture]
 * - Backend integration: createSession → uploadMedia → generateQuote
 * - Jetpack Compose UI with recording status indicator
 */
class RecordingActivity : ComponentActivity() {

    companion object {
        private const val TAG = "RecordingActivity"
        private const val BASE_URL = "https://backend-production-5320.up.railway.app"
    }

    private val audioRecorder by lazy { AudioRecorder(this) }
    private val videoCapture by lazy { VideoCapture() }

    private var shopId: String = ""

    // Permissions required by this screen
    private val requiredPermissions = arrayOf(
        Manifest.permission.RECORD_AUDIO,
        Manifest.permission.CAMERA,
        Manifest.permission.BLUETOOTH_CONNECT,
    )

    // -------------------------------------------------------------------------
    // Lifecycle
    // -------------------------------------------------------------------------

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        shopId = intent.getStringExtra("SHOP_ID") ?: ""

        requestPermissionsIfNeeded {
            // Permissions granted – UI is already set, nothing extra needed here.
        }

        setContent {
            MaterialTheme {
                RecordingScreen(
                    audioRecorder = audioRecorder,
                    videoCapture = videoCapture,
                    onStartRecording = { previewView ->
                        lifecycleScope.launch {
                            startCaptures(previewView)
                        }
                    },
                    onStopRecording = { onFilesReady ->
                        lifecycleScope.launch {
                            val files = stopCaptures()
                            onFilesReady(files.first, files.second)
                        }
                    },
                    onGenerateQuote = { sessionId, onResult ->
                        lifecycleScope.launch {
                            val quote = generateQuote(sessionId)
                            onResult(quote)
                        }
                    },
                    onUploadMedia = { sessionId, audioFile, videoFile, onDone ->
                        lifecycleScope.launch {
                            uploadMedia(sessionId, audioFile, videoFile)
                            onDone()
                        }
                    },
                    onCreateSession = { onSession ->
                        lifecycleScope.launch {
                            val id = createSession(shopId)
                            onSession(id)
                        }
                    },
                )
            }
        }
    }

    // -------------------------------------------------------------------------
    // Recording helpers
    // -------------------------------------------------------------------------

    private suspend fun startCaptures(previewView: PreviewView) {
        try {
            audioRecorder.startRecording()
            videoCapture.previewView = previewView
            videoCapture.startCapture(this)
        } catch (e: Exception) {
            Log.e(TAG, "Failed to start captures: ${e.message}", e)
        }
    }

    private fun stopCaptures(): Pair<File?, File?> {
        val audio = audioRecorder.stopRecording()
        val video = videoCapture.stopCapture()
        return Pair(audio, video)
    }

    // -------------------------------------------------------------------------
    // Backend API calls
    // -------------------------------------------------------------------------

    /**
     * POST /sessions – creates a new session and returns its ID.
     */
    private suspend fun createSession(shopId: String): String = withContext(Dispatchers.IO) {
        try {
            val url = URL("$BASE_URL/sessions")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 10_000
                readTimeout = 10_000
            }
            val body = JSONObject().apply {
                if (shopId.isNotBlank()) put("shop_id", shopId)
            }.toString()
            OutputStreamWriter(conn.outputStream).use { it.write(body) }
            val response = conn.inputStream.bufferedReader().readText()
            conn.disconnect()
            val json = JSONObject(response)
            json.optString("session_id", UUID.randomUUID().toString())
        } catch (e: Exception) {
            Log.e(TAG, "createSession failed: ${e.message}", e)
            UUID.randomUUID().toString()   // local fallback so the UI keeps working
        }
    }

    /**
     * POST /sessions/{id}/media – multipart upload of audio and video files.
     */
    private suspend fun uploadMedia(
        sessionId: String,
        audioFile: File?,
        videoFile: File?,
    ) = withContext(Dispatchers.IO) {
        if (audioFile == null && videoFile == null) return@withContext

        try {
            val boundary = "----AutoShopBoundary${System.currentTimeMillis()}"
            val url = URL("$BASE_URL/sessions/$sessionId/media")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "multipart/form-data; boundary=$boundary")
                doOutput = true
                connectTimeout = 30_000
                readTimeout = 60_000
            }

            conn.outputStream.use { out ->
                audioFile?.let { file ->
                    writePart(out, boundary, "audio", "audio.pcm", file.readBytes(), "audio/pcm")
                }
                videoFile?.let { file ->
                    writePart(out, boundary, "video", "video.mp4", file.readBytes(), "video/mp4")
                }
                out.write("--$boundary--\r\n".toByteArray())
            }

            val code = conn.responseCode
            Log.d(TAG, "uploadMedia → HTTP $code")
            conn.disconnect()
        } catch (e: Exception) {
            Log.e(TAG, "uploadMedia failed: ${e.message}", e)
        }
    }

    /**
     * POST /sessions/{id}/quote – asks the backend to generate an estimate.
     * Returns the quote text or an error message.
     */
    private suspend fun generateQuote(sessionId: String): String = withContext(Dispatchers.IO) {
        try {
            val url = URL("$BASE_URL/sessions/$sessionId/quote")
            val conn = (url.openConnection() as HttpURLConnection).apply {
                requestMethod = "POST"
                setRequestProperty("Content-Type", "application/json")
                doOutput = true
                connectTimeout = 30_000
                readTimeout = 60_000
            }
            OutputStreamWriter(conn.outputStream).use { it.write("{}") }
            val response = conn.inputStream.bufferedReader().readText()
            conn.disconnect()
            val json = JSONObject(response)
            json.optString("quote", response)
        } catch (e: Exception) {
            Log.e(TAG, "generateQuote failed: ${e.message}", e)
            "Error generating quote: ${e.message}"
        }
    }

    // -------------------------------------------------------------------------
    // Multipart helper
    // -------------------------------------------------------------------------

    private fun writePart(
        out: java.io.OutputStream,
        boundary: String,
        name: String,
        filename: String,
        data: ByteArray,
        mimeType: String,
    ) {
        val header = buildString {
            append("--$boundary\r\n")
            append("Content-Disposition: form-data; name=\"$name\"; filename=\"$filename\"\r\n")
            append("Content-Type: $mimeType\r\n\r\n")
        }
        out.write(header.toByteArray())
        out.write(data)
        out.write("\r\n".toByteArray())
    }

    // -------------------------------------------------------------------------
    // Permission handling
    // -------------------------------------------------------------------------

    private fun requestPermissionsIfNeeded(onGranted: () -> Unit) {
        val missing = requiredPermissions.filter {
            ContextCompat.checkSelfPermission(this, it) != PackageManager.PERMISSION_GRANTED
        }
        if (missing.isEmpty()) {
            onGranted()
            return
        }
        val launcher = registerForActivityResult(
            ActivityResultContracts.RequestMultiplePermissions()
        ) { results ->
            val allGranted = results.values.all { it }
            if (allGranted) onGranted()
            else Log.w(TAG, "Some permissions were denied: ${results.filter { !it.value }.keys}")
        }
        launcher.launch(missing.toTypedArray())
    }
}

// =============================================================================
// Composable UI
// =============================================================================

/**
 * Full-screen recording UI.
 *
 * State machine:
 *  IDLE → (Start) → RECORDING → (Stop) → STOPPED → (Generate Quote) → QUOTED
 *                                       ↑_______________(Start again)_↗
 */
@Composable
fun RecordingScreen(
    audioRecorder: AudioRecorder,
    videoCapture: VideoCapture,
    onStartRecording: (PreviewView) -> Unit,
    onStopRecording: (onFilesReady: (File?, File?) -> Unit) -> Unit,
    onCreateSession: (onSession: (String) -> Unit) -> Unit,
    onUploadMedia: (sessionId: String, audio: File?, video: File?, onDone: () -> Unit) -> Unit,
    onGenerateQuote: (sessionId: String, onResult: (String) -> Unit) -> Unit,
) {
    // ---- State ----
    var isRecording by remember { mutableStateOf(false) }
    var sessionId by remember { mutableStateOf<String?>(null) }
    var quoteText by remember { mutableStateOf<String?>(null) }
    var statusMessage by remember { mutableStateOf("Ready") }
    var isLoading by remember { mutableStateOf(false) }

    // Hold files between stop and upload/quote
    var pendingAudio by remember { mutableStateOf<File?>(null) }
    var pendingVideo by remember { mutableStateOf<File?>(null) }

    // PreviewView reference kept stable across recompositions
    val previewViewRef = remember { mutableStateOf<PreviewView?>(null) }

    Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {

            // ---- Header row: status indicator + session ID ----
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                RecordingIndicator(isRecording = isRecording)
                Text(
                    text = sessionId?.let { "Session: ${it.take(8)}…" } ?: "No session",
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }

            Spacer(modifier = Modifier.height(8.dp))

            // ---- Camera preview ----
            CameraPreview(
                modifier = Modifier
                    .fillMaxWidth()
                    .weight(1f),
                onPreviewViewCreated = { pv ->
                    previewViewRef.value = pv
                },
            )

            Spacer(modifier = Modifier.height(12.dp))

            // ---- Status message ----
            Text(
                text = statusMessage,
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
            )

            Spacer(modifier = Modifier.height(12.dp))

            // ---- Control buttons ----
            Row(
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                // Start button
                Button(
                    onClick = {
                        if (!isRecording) {
                            isLoading = true
                            statusMessage = "Starting session…"
                            onCreateSession { id ->
                                sessionId = id
                                val pv = previewViewRef.value
                                if (pv != null) {
                                    onStartRecording(pv)
                                    isRecording = true
                                    quoteText = null
                                    statusMessage = "Recording…"
                                } else {
                                    statusMessage = "Camera not ready"
                                }
                                isLoading = false
                            }
                        }
                    },
                    enabled = !isRecording && !isLoading,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32)),
                ) {
                    Text("Start")
                }

                // Stop button
                Button(
                    onClick = {
                        if (isRecording) {
                            isRecording = false
                            isLoading = true
                            statusMessage = "Stopping…"
                            onStopRecording { audio, video ->
                                pendingAudio = audio
                                pendingVideo = video
                                val sid = sessionId
                                if (sid != null) {
                                    statusMessage = "Uploading media…"
                                    onUploadMedia(sid, audio, video) {
                                        statusMessage = "Upload complete. Ready to generate quote."
                                        isLoading = false
                                    }
                                } else {
                                    statusMessage = "Stopped (no session to upload)"
                                    isLoading = false
                                }
                            }
                        }
                    },
                    enabled = isRecording && !isLoading,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFC62828)),
                ) {
                    Text("Stop")
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // ---- Generate Quote button ----
            Button(
                onClick = {
                    val sid = sessionId ?: return@Button
                    isLoading = true
                    statusMessage = "Generating quote…"
                    onGenerateQuote(sid) { quote ->
                        quoteText = quote
                        statusMessage = "Quote ready"
                        isLoading = false
                    }
                },
                enabled = !isRecording && sessionId != null && !isLoading,
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text("Generate Quote")
            }

            // ---- Loading indicator ----
            if (isLoading) {
                Spacer(modifier = Modifier.height(8.dp))
                CircularProgressIndicator(modifier = Modifier.size(24.dp), strokeWidth = 2.dp)
            }

            // ---- Quote display ----
            quoteText?.let { quote ->
                Spacer(modifier = Modifier.height(12.dp))
                QuoteCard(quote = quote)
            }

            Spacer(modifier = Modifier.height(8.dp))
        }
    }
}

// =============================================================================
// Sub-composables
// =============================================================================

/**
 * Animated red pulsing dot that indicates recording is active.
 */
@Composable
fun RecordingIndicator(isRecording: Boolean) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(14.dp)
                .background(
                    color = if (isRecording) Color.Red else Color.Gray,
                    shape = CircleShape,
                ),
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = if (isRecording) "REC" else "IDLE",
            fontSize = 12.sp,
            color = if (isRecording) Color.Red else Color.Gray,
        )
    }
}

/**
 * Hosts a CameraX [PreviewView] inside a Compose layout via [AndroidView].
 */
@Composable
fun CameraPreview(
    modifier: Modifier = Modifier,
    onPreviewViewCreated: (PreviewView) -> Unit,
) {
    val context = LocalContext.current
    AndroidView(
        modifier = modifier,
        factory = { ctx ->
            PreviewView(ctx).also { pv ->
                pv.implementationMode = PreviewView.ImplementationMode.COMPATIBLE
                onPreviewViewCreated(pv)
            }
        },
        update = { /* no dynamic updates needed */ },
    )
}

/**
 * Card that displays the generated repair quote.
 */
@Composable
fun QuoteCard(quote: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
    ) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(
                text = "Estimated Quote",
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(modifier = Modifier.height(4.dp))
            Text(
                text = quote,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurface,
            )
        }
    }
}
