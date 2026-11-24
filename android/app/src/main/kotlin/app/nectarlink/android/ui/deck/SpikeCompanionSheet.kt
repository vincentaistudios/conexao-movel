// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.deck

import android.content.Context
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.view.HapticFeedbackConstants
import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.tween
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import java.util.Locale

// Constantes canônicas de Valorant
const val VALORANT_SPIKE_EXPLODE_SECONDS = 40.0f
const val VALORANT_FULL_DEFUSE_SECONDS = 7.0f
const val VALORANT_HALF_DEFUSE_SECONDS = 3.5f
const val VALORANT_FULL_DEFUSE_CUTOFF = 33.0f // 40 - 7
const val VALORANT_HALF_DEFUSE_CUTOFF = 36.5f // 40 - 3.5

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SpikeCompanionSheet(
    initialPlantedTimestampMs: Long = 0L,
    latencyCompensationMs: Long = 0L,
    onDismiss: () -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    val context = LocalContext.current
    val view = LocalView.current
    val scope = rememberCoroutineScope()

    val audioHelper = remember { SpikeAudioHelper(scope) }
    var audioEnabled by remember { mutableStateOf(true) }
    var hapticsEnabled by remember { mutableStateOf(true) }

    // Estados de temporização
    var isPlanted by remember { mutableStateOf(true) }
    var isDefused by remember { mutableStateOf(false) }
    var startTimestamp by remember {
        mutableLongStateOf(
            if (initialPlantedTimestampMs > 0) initialPlantedTimestampMs - latencyCompensationMs
            else System.currentTimeMillis()
        )
    }
    var elapsedSeconds by remember { mutableFloatStateOf(0.0f) }

    // Simulador de ação em andamento
    var defusingActive by remember { mutableStateOf(false) }
    var hasHalfDefuseCheckpoint by remember { mutableStateOf(false) }
    var defuseStartTimestamp by remember { mutableLongStateOf(0L) }
    var defuseElapsedSeconds by remember { mutableFloatStateOf(0.0f) }

    // Obter serviço de vibração do Android
    val vibrator = remember {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val manager = context.getSystemService(Context.VIBRATOR_MANAGER_SERVICE) as? VibratorManager
            manager?.defaultVibrator
        } else {
            @Suppress("DEPRECATION")
            context.getSystemService(Context.VIBRATOR_SERVICE) as? Vibrator
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            vibrator?.cancel()
        }
    }

    // Loop de precisão em milissegundos
    LaunchedEffect(isPlanted, isDefused, startTimestamp) {
        if (!isPlanted || isDefused) return@LaunchedEffect

        var lastHapticTick = 0L
        while (isActive && isPlanted && !isDefused) {
            val now = System.currentTimeMillis()
            val elapsed = (now - startTimestamp).toFloat() / 1000.0f
            elapsedSeconds = elapsed.coerceAtMost(VALORANT_SPIKE_EXPLODE_SECONDS)

            if (elapsedSeconds >= VALORANT_SPIKE_EXPLODE_SECONDS) {
                if (audioEnabled) audioHelper.playWarningTone()
                break
            }

            // Ritmo dinâmico de haptics e bipes acelerando conforme a fase
            val tickIntervalMs = when {
                elapsedSeconds < 20.0f -> 1000L
                elapsedSeconds < 30.0f -> 500L
                elapsedSeconds < 33.0f -> 250L
                elapsedSeconds < 36.5f -> 180L
                else -> 120L
            }

            if (now - lastHapticTick >= tickIntervalMs) {
                lastHapticTick = now
                if (hapticsEnabled) {
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        val amplitude = if (elapsedSeconds >= VALORANT_HALF_DEFUSE_CUTOFF) 255 else 180
                        vibrator?.vibrate(VibrationEffect.createOneShot(35, amplitude))
                    } else {
                        view.performHapticFeedback(HapticFeedbackConstants.CLOCK_TICK)
                    }
                }
                if (audioEnabled) {
                    val freq = if (elapsedSeconds >= VALORANT_HALF_DEFUSE_CUTOFF) 1200.0 else 880.0
                    audioHelper.playTickingBeep(frequencyHz = freq, durationMs = 30)
                }
            }

            // Atualização do cálculo do simulador de defuse se ativo
            if (defusingActive) {
                defuseElapsedSeconds = (now - defuseStartTimestamp).toFloat() / 1000.0f
                val requiredSeconds = if (hasHalfDefuseCheckpoint) VALORANT_HALF_DEFUSE_SECONDS else VALORANT_FULL_DEFUSE_SECONDS
                if (!hasHalfDefuseCheckpoint && defuseElapsedSeconds >= VALORANT_HALF_DEFUSE_SECONDS) {
                    hasHalfDefuseCheckpoint = true
                    if (audioEnabled) audioHelper.playHalfDefuseTone()
                }
                if (defuseElapsedSeconds >= requiredSeconds) {
                    isDefused = true
                    defusingActive = false
                    if (audioEnabled) audioHelper.playHalfDefuseTone(350)
                }
            }

            delay(33) // ~30 fps para suavidade máxima
        }
    }

    val remainingSeconds = (VALORANT_SPIKE_EXPLODE_SECONDS - elapsedSeconds).coerceAtLeast(0.0f)
    val isDetonated = elapsedSeconds >= VALORANT_SPIKE_EXPLODE_SECONDS && !isDefused

    // Matriz cromática explícita: Verde (0-33s) -> Amarelo (33-36.5s) -> Vermelho (36.5-40s)
    val phaseColor by animateColorAsState(
        targetValue = when {
            isDefused -> Color(0xFF00E676) // Verde Vitória
            isDetonated -> Color(0xFFFF1744) // Vermelho Detonado
            elapsedSeconds < VALORANT_FULL_DEFUSE_CUTOFF -> Color(0xFF00E5FF) // Ciano / Verde Radianita (Seguro)
            elapsedSeconds < VALORANT_HALF_DEFUSE_CUTOFF -> Color(0xFFFFD600) // Amarelo Alerta (No Limite)
            else -> Color(0xFFFF1744) // Vermelho Rubi (Não Dá Mais)
        },
        animationSpec = tween(durationMillis = 200, easing = FastOutSlowInEasing),
        label = "SpikePhaseColor",
    )

    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = MaterialTheme.colorScheme.surfaceContainerLowest,
        shape = RoundedCornerShape(topStart = 24.dp, topEnd = 24.dp),
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            // Cabeçalho tático com latência compensada
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    SpikeIcon(color = phaseColor, size = 22.dp)
                    Spacer(Modifier.width(8.dp))
                    Text(
                        text = "SPIKE COMPANION",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.2.sp,
                    )
                }

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.surfaceContainerHigh,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                ) {
                    Text(
                        text = if (latencyCompensationMs > 0) "LAT: ${latencyCompensationMs}ms (Compensado)" else "SINC: 0ms Local",
                        style = MaterialTheme.typography.labelSmall,
                        fontFamily = FontFamily.Monospace,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
                    )
                }
            }

            Spacer(Modifier.height(16.dp))

            // Card Principal do Cronômetro Tático
            Card(
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(18.dp),
                colors = CardDefaults.cardColors(
                    containerColor = MaterialTheme.colorScheme.surfaceContainerHigh,
                ),
                border = BorderStroke(2.dp, phaseColor.copy(alpha = 0.8f)),
            ) {
                Column(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(vertical = 18.dp, horizontal = 16.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    if (isDefused) {
                        DefuseShieldIcon(color = Color(0xFF00E676), size = 44.dp)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            text = "SPIKE DESARMADA",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF00E676),
                        )
                    } else if (isDetonated) {
                        SpikeExplosionIcon(color = Color(0xFFFF1744), size = 52.dp)
                        Spacer(Modifier.height(8.dp))
                        Text(
                            text = "DETONAÇÃO DA SPIKE",
                            style = MaterialTheme.typography.headlineSmall,
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFFFF1744),
                        )
                    } else {
                        // Display dos 40 segundos restantes com milissegundos
                        val formattedSeconds = String.format(Locale.US, "%.1f", remainingSeconds)
                        Row(verticalAlignment = Alignment.Bottom) {
                            Text(
                                text = formattedSeconds,
                                fontSize = 54.sp,
                                fontWeight = FontWeight.Black,
                                fontFamily = FontFamily.Monospace,
                                color = phaseColor,
                            )
                            Text(
                                text = "s",
                                fontSize = 24.sp,
                                fontWeight = FontWeight.Bold,
                                color = phaseColor.copy(alpha = 0.7f),
                                modifier = Modifier.padding(bottom = 8.dp, start = 2.dp),
                            )
                        }

                        // Badge de status de defuse conforme a cor
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = phaseColor.copy(alpha = 0.15f),
                            border = BorderStroke(1.dp, phaseColor.copy(alpha = 0.6f)),
                        ) {
                            val statusText = when {
                                elapsedSeconds < VALORANT_FULL_DEFUSE_CUTOFF -> "DEFUSE INTEGRAL POSSÍVEL"
                                elapsedSeconds < VALORANT_HALF_DEFUSE_CUTOFF -> "NO LIMITE: APENAS HALF DEFUSE!"
                                else -> "NÃO DÁ MAIS! CORRA DA EXPLOSÃO!"
                            }
                            Text(
                                text = statusText,
                                style = MaterialTheme.typography.labelMedium,
                                fontWeight = FontWeight.ExtraBold,
                                color = phaseColor,
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
                            )
                        }
                    }

                    Spacer(Modifier.height(14.dp))

                    // Barra de progresso linear tática com marcas dos 33s e 36.5s
                    val progress = (elapsedSeconds / VALORANT_SPIKE_EXPLODE_SECONDS).coerceIn(0.0f, 1.0f)
                    LinearProgressIndicator(
                        progress = { progress },
                        modifier = Modifier
                            .fillMaxWidth()
                            .height(10.dp)
                            .clip(RoundedCornerShape(5.dp)),
                        color = phaseColor,
                        trackColor = MaterialTheme.colorScheme.surfaceContainerHighest,
                    )

                    Spacer(Modifier.height(8.dp))

                    // Marcadores de tempo abaixo da barra
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("0s (Plant)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("33s (Full)", style = MaterialTheme.typography.bodySmall, color = Color(0xFFFFD600), fontWeight = FontWeight.Bold)
                        Text("36.5s (Half)", style = MaterialTheme.typography.bodySmall, color = Color(0xFFFF1744), fontWeight = FontWeight.Bold)
                        Text("40s (Explode)", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }

            Spacer(Modifier.height(14.dp))

            // Painel de Informações Táticas Avançadas
            Surface(
                shape = RoundedCornerShape(14.dp),
                color = MaterialTheme.colorScheme.surfaceContainer,
                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Column(modifier = Modifier.padding(12.dp)) {
                    val fullDefuseMargin = (VALORANT_FULL_DEFUSE_CUTOFF - elapsedSeconds)
                    val halfDefuseMargin = (VALORANT_HALF_DEFUSE_CUTOFF - elapsedSeconds)
                    val safeSaveWeaponSeconds = (32.0f - elapsedSeconds)

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Janela Defuse Completo (7.0s):", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                        Text(
                            text = if (fullDefuseMargin > 0) String.format(Locale.US, "Restam %.1fs", fullDefuseMargin) else "Esgotado",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Bold,
                            color = if (fullDefuseMargin > 0) Color(0xFF00E5FF) else Color(0xFFFF1744),
                        )
                    }

                    Spacer(Modifier.height(4.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Janela Half Defuse (3.5s):", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                        Text(
                            text = if (halfDefuseMargin > 0) String.format(Locale.US, "Restam %.1fs", halfDefuseMargin) else "Esgotado",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.Bold,
                            color = if (halfDefuseMargin > 0) Color(0xFFFFD600) else Color(0xFFFF1744),
                        )
                    }

                    Spacer(Modifier.height(4.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text("Economia (Salvar Vandal/Phantom):", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                        Text(
                            text = if (safeSaveWeaponSeconds > 0) String.format(Locale.US, "Correr em %.1fs", safeSaveWeaponSeconds) else "Saia Já!",
                            style = MaterialTheme.typography.bodySmall,
                            fontWeight = FontWeight.SemiBold,
                            color = if (safeSaveWeaponSeconds > 0) MaterialTheme.colorScheme.primary else Color(0xFFFF1744),
                        )
                    }
                }
            }

            Spacer(Modifier.height(14.dp))

            // Botões de Ação Dinâmica de Jogo
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                // Botão de Defuse / Desarme
                FilledTonalButton(
                    onClick = {
                        view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                        if (!defusingActive && !isDefused && !isDetonated) {
                            defusingActive = true
                            defuseStartTimestamp = System.currentTimeMillis()
                            if (audioEnabled) audioHelper.playDefuseInitialTone()
                        } else {
                            defusingActive = false
                        }
                    },
                    modifier = Modifier.weight(1f),
                    colors = ButtonDefaults.filledTonalButtonColors(
                        containerColor = if (defusingActive) Color(0xFFFFD600) else MaterialTheme.colorScheme.primaryContainer,
                        contentColor = if (defusingActive) Color.Black else MaterialTheme.colorScheme.onPrimaryContainer,
                    ),
                    shape = RoundedCornerShape(12.dp),
                ) {
                    Text(
                        text = if (defusingActive) "Cancelando Defuse" else "Iniciei Desarme",
                        fontWeight = FontWeight.Bold,
                    )
                }

                // Botão de Spike Desarmada (Vitória)
                OutlinedButton(
                    onClick = {
                        view.performHapticFeedback(HapticFeedbackConstants.CONFIRM)
                        isDefused = true
                        defusingActive = false
                    },
                    modifier = Modifier.weight(1f),
                    shape = RoundedCornerShape(12.dp),
                    border = BorderStroke(1.dp, Color(0xFF00E676)),
                ) {
                    Text(
                        text = "Spike Desarmada",
                        color = Color(0xFF00E676),
                        fontWeight = FontWeight.Bold,
                    )
                }
            }

            Spacer(Modifier.height(10.dp))

            // Linha de utilitários: Reiniciar / Nova Rodada, Toggle Áudio, Toggle Vibração
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                TextButton(
                    onClick = {
                        view.performHapticFeedback(HapticFeedbackConstants.KEYBOARD_TAP)
                        startTimestamp = System.currentTimeMillis()
                        elapsedSeconds = 0.0f
                        isDefused = false
                        isPlanted = true
                        defusingActive = false
                        hasHalfDefuseCheckpoint = false
                    }
                ) {
                    Text("Reiniciar Rodada", fontWeight = FontWeight.SemiBold)
                }

                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    Surface(
                        shape = CircleShape,
                        color = if (audioEnabled) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                        modifier = Modifier
                            .size(36.dp)
                            .clickable {
                                audioEnabled = !audioEnabled
                                audioHelper.setMuted(!audioEnabled)
                            },
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = if (audioEnabled) "Som" else "Mudo",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }

                    Surface(
                        shape = CircleShape,
                        color = if (hapticsEnabled) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                        modifier = Modifier
                            .size(36.dp)
                            .clickable {
                                hapticsEnabled = !hapticsEnabled
                            },
                        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Text(
                                text = if (hapticsEnabled) "Vib" else "Off",
                                style = MaterialTheme.typography.labelSmall,
                                fontWeight = FontWeight.Bold,
                            )
                        }
                    }
                }
            }

            Spacer(Modifier.height(16.dp))
        }
    }
}

