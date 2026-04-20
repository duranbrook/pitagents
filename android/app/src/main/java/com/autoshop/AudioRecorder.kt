package com.autoshop

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.MediaRecorder
import android.util.Log
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.launch
import java.io.File
import java.io.FileOutputStream

/**
 * Captures audio from a Bluetooth headset (or fallback microphone) using
 * the low-level [AudioRecord] API and writes raw PCM data to a temp file.
 *
 * Typical usage:
 * ```
 * val recorder = AudioRecorder(context)
 * recorder.startRecording()
 * // … later …
 * val audioFile: File? = recorder.stopRecording()
 * ```
 */
class AudioRecorder(private val context: Context) {

    companion object {
        private const val TAG = "AudioRecorder"
        private const val SAMPLE_RATE = 16_000        // 16 kHz – good for speech
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }

    private var audioRecord: AudioRecord? = null
    private var outputFile: File? = null
    private var recordingJob: Job? = null
    private var isRecording = false

    private val audioManager: AudioManager by lazy {
        context.getSystemService(Context.AUDIO_SERVICE) as AudioManager
    }

    // -------------------------------------------------------------------------
    // Public API
    // -------------------------------------------------------------------------

    /**
     * Starts recording audio.
     *
     * Requires [Manifest.permission.RECORD_AUDIO] to be granted before calling.
     * Routes audio through the connected Bluetooth SCO device when available,
     * otherwise falls back to the device microphone.
     *
     * @throws SecurityException if RECORD_AUDIO permission is not granted.
     * @throws IllegalStateException if recording is already in progress.
     */
    fun startRecording() {
        check(!isRecording) { "Recording is already in progress." }
        requirePermission()

        enableBluetoothSco()

        val bufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
            .takeIf { it != AudioRecord.ERROR && it != AudioRecord.ERROR_BAD_VALUE }
            ?: (SAMPLE_RATE * 2)   // 1-second fallback buffer

        audioRecord = AudioRecord(
            MediaRecorder.AudioSource.VOICE_COMMUNICATION,
            SAMPLE_RATE,
            CHANNEL_CONFIG,
            AUDIO_FORMAT,
            bufferSize
        ).also { record ->
            if (record.state != AudioRecord.STATE_INITIALIZED) {
                Log.w(TAG, "AudioRecord failed to initialize; retrying with MIC source.")
                record.release()
                // Retry with plain MIC source as a safety fallback
                return@also AudioRecord(
                    MediaRecorder.AudioSource.MIC,
                    SAMPLE_RATE,
                    CHANNEL_CONFIG,
                    AUDIO_FORMAT,
                    bufferSize
                )
            }
        }

        outputFile = createTempFile("audio_", ".pcm")
        isRecording = true
        audioRecord!!.startRecording()

        recordingJob = CoroutineScope(Dispatchers.IO).launch {
            writeAudioToFile(audioRecord!!, outputFile!!, bufferSize)
        }

        Log.d(TAG, "Recording started → ${outputFile?.absolutePath}")
    }

    /**
     * Stops the current recording session.
     *
     * @return The [File] containing the raw PCM audio, or `null` if recording
     *         was never started.
     */
    fun stopRecording(): File? {
        if (!isRecording) {
            Log.w(TAG, "stopRecording() called but no recording is in progress.")
            return null
        }

        isRecording = false
        recordingJob?.cancel()
        recordingJob = null

        audioRecord?.apply {
            stop()
            release()
        }
        audioRecord = null

        disableBluetoothSco()

        Log.d(TAG, "Recording stopped → ${outputFile?.absolutePath}")
        return outputFile
    }

    // -------------------------------------------------------------------------
    // Internal helpers
    // -------------------------------------------------------------------------

    /** Continuously reads PCM samples from [record] and writes them to [file]. */
    private fun writeAudioToFile(record: AudioRecord, file: File, bufferSize: Int) {
        val buffer = ByteArray(bufferSize)
        FileOutputStream(file).use { out ->
            while (isRecording) {
                val bytesRead = record.read(buffer, 0, buffer.size)
                if (bytesRead > 0) {
                    out.write(buffer, 0, bytesRead)
                }
            }
        }
    }

    /** Routes audio to the Bluetooth SCO device if one is connected. */
    private fun enableBluetoothSco() {
        try {
            audioManager.mode = AudioManager.MODE_IN_COMMUNICATION
            audioManager.isBluetoothScoOn = true
            audioManager.startBluetoothSco()
            Log.d(TAG, "Bluetooth SCO started.")
        } catch (e: Exception) {
            Log.w(TAG, "Could not start Bluetooth SCO: ${e.message}")
        }
    }

    /** Restores audio routing to normal after recording. */
    private fun disableBluetoothSco() {
        try {
            audioManager.stopBluetoothSco()
            audioManager.isBluetoothScoOn = false
            audioManager.mode = AudioManager.MODE_NORMAL
            Log.d(TAG, "Bluetooth SCO stopped.")
        } catch (e: Exception) {
            Log.w(TAG, "Could not stop Bluetooth SCO: ${e.message}")
        }
    }

    /** Creates a temp file in the app's cache directory. */
    private fun createTempFile(prefix: String, suffix: String): File =
        File.createTempFile(prefix, suffix, context.cacheDir)

    /** Throws [SecurityException] when RECORD_AUDIO is not granted. */
    private fun requirePermission() {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO)
            != PackageManager.PERMISSION_GRANTED
        ) {
            throw SecurityException(
                "RECORD_AUDIO permission is required before calling startRecording()."
            )
        }
    }
}
