// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.deck

import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioTrack
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlin.math.sin

/**
 * Sintetizador nativo de audio PCM para o Spike Companion do Valorant.
 * Gera ondas senoidais puras em tempo real via AudioTrack sem necessidade de arquivos externos,
 * reproduzindo os bipes de ticking, o tom de desarme padrão (0-3.5s) e o tom agudo característico
 * da metade do defuse (3.5s-7.0s).
 */
class SpikeAudioHelper(
    private val scope: CoroutineScope,
) {
    private val sampleRate = 44100
    private var isMuted = false

    fun setMuted(muted: Boolean) {
        isMuted = muted
    }

    fun isMuted(): Boolean = isMuted

    /**
     * Toca um bipe curto de pulsação da Spike (880 Hz, 40ms).
     */
    fun playTickingBeep(frequencyHz: Double = 880.0, durationMs: Int = 40) {
        if (isMuted) return
        scope.launch(Dispatchers.Default) {
            playTone(frequencyHz, durationMs, volume = 0.5f)
        }
    }

    /**
     * Toca o tom grave do início do desarme (440 Hz).
     */
    fun playDefuseInitialTone(durationMs: Int = 180) {
        if (isMuted) return
        scope.launch(Dispatchers.Default) {
            playTone(440.0, durationMs, volume = 0.6f)
        }
    }

    /**
     * Toca o tom agudo de checkpoint da metade do defuse (880 Hz com harmônico 1320 Hz).
     */
    fun playHalfDefuseTone(durationMs: Int = 220) {
        if (isMuted) return
        scope.launch(Dispatchers.Default) {
            playDualTone(880.0, 1320.0, durationMs, volume = 0.7f)
        }
    }

    /**
     * Toca alerta agudo de detonação iminente / recuo tático (1175 Hz).
     */
    fun playWarningTone() {
        if (isMuted) return
        scope.launch(Dispatchers.Default) {
            playTone(1174.66, 120, volume = 0.8f)
        }
    }

    private fun playTone(freqHz: Double, durationMs: Int, volume: Float) {
        try {
            val numSamples = (durationMs * sampleRate) / 1000
            val buffer = ShortArray(numSamples)
            val fadeCount = (numSamples * 0.15).toInt().coerceAtLeast(1)

            for (i in 0 until numSamples) {
                val time = i.toDouble() / sampleRate
                val rawSample = sin(2.0 * Math.PI * freqHz * time)

                // Aplica envelope de fade-in e fade-out suave para evitar cliques no alto-falante
                val envelope = when {
                    i < fadeCount -> i.toFloat() / fadeCount
                    i > numSamples - fadeCount -> (numSamples - i).toFloat() / fadeCount
                    else -> 1.0f
                }

                val amp = (rawSample * Short.MAX_VALUE * volume * envelope).toInt()
                buffer[i] = amp.coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
            }

            writeAudio(buffer)
        } catch (_: Exception) {
            // Ignora silenciosamente em caso de erro de áudio
        }
    }

    private fun playDualTone(freq1: Double, freq2: Double, durationMs: Int, volume: Float) {
        try {
            val numSamples = (durationMs * sampleRate) / 1000
            val buffer = ShortArray(numSamples)
            val fadeCount = (numSamples * 0.15).toInt().coerceAtLeast(1)

            for (i in 0 until numSamples) {
                val time = i.toDouble() / sampleRate
                val sample1 = sin(2.0 * Math.PI * freq1 * time)
                val sample2 = sin(2.0 * Math.PI * freq2 * time)
                val mixed = (sample1 + sample2) * 0.5

                val envelope = when {
                    i < fadeCount -> i.toFloat() / fadeCount
                    i > numSamples - fadeCount -> (numSamples - i).toFloat() / fadeCount
                    else -> 1.0f
                }

                val amp = (mixed * Short.MAX_VALUE * volume * envelope).toInt()
                buffer[i] = amp.coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
            }

            writeAudio(buffer)
        } catch (_: Exception) {
            // Ignora silenciosamente em caso de falha de codec
        }
    }

    private fun writeAudio(buffer: ShortArray) {
        var track: AudioTrack? = null
        try {
            val bufferSize = buffer.size * 2
            track = AudioTrack.Builder()
                .setAudioAttributes(
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_GAME)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build()
                )
                .setAudioFormat(
                    AudioFormat.Builder()
                        .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                        .setSampleRate(sampleRate)
                        .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                        .build()
                )
                .setBufferSizeInBytes(bufferSize)
                .setTransferMode(AudioTrack.MODE_STATIC)
                .build()

            track.write(buffer, 0, buffer.size)
            track.play()
            Thread.sleep((buffer.size * 1000L / sampleRate) + 20)
        } catch (_: Exception) {
            // Proteção contra interrupções de thread
        } finally {
            try {
                track?.stop()
                track?.release()
            } catch (_: Exception) {}
        }
    }
}

