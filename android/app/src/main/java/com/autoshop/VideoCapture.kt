package com.autoshop

import android.content.Context
import android.util.Log
import androidx.camera.core.CameraSelector
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.video.FileOutputOptions
import androidx.camera.video.Quality
import androidx.camera.video.QualitySelector
import androidx.camera.video.Recorder
import androidx.camera.video.Recording
import androidx.camera.video.VideoCapture as CameraXVideoCapture
import androidx.camera.video.VideoRecordEvent
import androidx.camera.view.PreviewView
import androidx.core.content.ContextCompat
import androidx.lifecycle.LifecycleOwner
import java.io.File
import java.util.concurrent.Executor
import kotlin.coroutines.resume
import kotlin.coroutines.suspendCoroutine

/**
 * Wraps CameraX video recording into a simple start/stop API.
 *
 * Attach a [PreviewView] from the UI layer via [previewView] before calling
 * [startCapture] so the live camera feed is displayed to the user.
 *
 * Typical usage:
 * ```
 * val videoCapture = VideoCapture()
 * videoCapture.previewView = myPreviewView
 * videoCapture.startCapture(context)
 * // … later …
 * val videoFile: File? = videoCapture.stopCapture()
 * ```
 */
class VideoCapture {

    companion object {
        private const val TAG = "VideoCapture"
    }

    /** Attach a [PreviewView] before calling [startCapture] to display the live feed. */
    var previewView: PreviewView? = null

    private var activeRecording: Recording? = null
    private var outputFile: File? = null
    private var cameraProvider: ProcessCameraProvider? = null

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    /**
     * Binds CameraX use cases and starts video recording.
     *
     * The [context] must also implement [LifecycleOwner] (e.g. an Activity or
     * Fragment). Audio is captured alongside video via [withAudioEnabled].
     *
     * @param context An Activity / Fragment context that implements [LifecycleOwner].
     */
    suspend fun startCapture(context: Context) {
        check(activeRecording == null) { "A recording is already in progress." }

        val lifecycleOwner = context as? LifecycleOwner
            ?: error("context must implement LifecycleOwner")

        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)
        val provider = suspendCoroutine<ProcessCameraProvider> { cont ->
            cameraProviderFuture.addListener(
                { cont.resume(cameraProviderFuture.get()) },
                ContextCompat.getMainExecutor(context)
            )
        }
        cameraProvider = provider

        // --- Preview use case ---
        val preview = Preview.Builder().build().also { prev ->
            previewView?.let { prev.setSurfaceProvider(it.surfaceProvider) }
        }

        // --- Video capture use case ---
        val recorder = Recorder.Builder()
            .setQualitySelector(QualitySelector.from(Quality.HD))
            .build()
        val videoCapture = CameraXVideoCapture.withOutput(recorder)

        // Unbind any previously bound use cases before rebinding
        provider.unbindAll()
        provider.bindToLifecycle(
            lifecycleOwner,
            CameraSelector.DEFAULT_BACK_CAMERA,
            preview,
            videoCapture
        )

        outputFile = createTempFile(context)

        val outputOptions = FileOutputOptions.Builder(outputFile!!).build()
        val mainExecutor: Executor = ContextCompat.getMainExecutor(context)

        activeRecording = videoCapture.output
            .prepareRecording(context, outputOptions)
            .withAudioEnabled()
            .start(mainExecutor) { event ->
                handleRecordEvent(event)
            }

        Log.d(TAG, "Video capture started → ${outputFile?.absolutePath}")
    }

    /**
     * Stops the active recording and releases camera resources.
     *
     * @return The [File] containing the recorded video, or `null` if capture
     *         was never started.
     */
    fun stopCapture(): File? {
        if (activeRecording == null) {
            Log.w(TAG, "stopCapture() called but no capture is in progress.")
            return null
        }

        activeRecording?.stop()
        activeRecording = null

        cameraProvider?.unbindAll()
        cameraProvider = null

        Log.d(TAG, "Video capture stopped → ${outputFile?.absolutePath}")
        return outputFile
    }

    // -------------------------------------------------------------------------
    // Internal helpers
    // -------------------------------------------------------------------------

    private fun handleRecordEvent(event: VideoRecordEvent) {
        when (event) {
            is VideoRecordEvent.Start -> {
                Log.d(TAG, "VideoRecordEvent.Start received.")
            }
            is VideoRecordEvent.Pause -> {
                Log.d(TAG, "VideoRecordEvent.Pause received.")
            }
            is VideoRecordEvent.Resume -> {
                Log.d(TAG, "VideoRecordEvent.Resume received.")
            }
            is VideoRecordEvent.Status -> {
                val stats = event.recordingStats
                Log.v(TAG, "VideoRecordEvent.Status: ${stats.recordedDurationNanos / 1_000_000} ms recorded.")
            }
            is VideoRecordEvent.Finalize -> {
                if (event.hasError()) {
                    Log.e(TAG, "VideoRecordEvent.Finalize error (${event.error}): ${event.cause?.message}")
                } else {
                    Log.d(TAG, "VideoRecordEvent.Finalize: recording saved to ${event.outputResults.outputUri}")
                }
            }
            else -> Log.v(TAG, "Unhandled VideoRecordEvent: $event")
        }
    }

    private fun createTempFile(context: Context): File =
        File.createTempFile("video_", ".mp4", context.cacheDir)
}
