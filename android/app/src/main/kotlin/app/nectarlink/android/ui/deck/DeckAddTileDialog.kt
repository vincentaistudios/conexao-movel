// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.deck

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp

data class DeckPresetItem(
    val id: String,
    val name: String,
    val subtitle: String,
    val icon: String,
    val color: String,
)

val DECK_PRESET_LIST = listOf(
    DeckPresetItem("spotify", "Spotify", "Musica e Podcast", "music", "emerald"),
    DeckPresetItem("minecraft", "Minecraft", "Jogo e Mundo", "gamepad", "amber"),
    DeckPresetItem("discord", "Discord", "Chat e Voz", "chat", "indigo"),
    DeckPresetItem("obs", "OBS Studio", "Gravacao e Live", "video", "ruby"),
    DeckPresetItem("browser", "Navegador Web", "Internet", "globe", "sapphire"),
    DeckPresetItem("twitch", "Twitch", "Transmissoes ao Vivo", "video", "purple"),
    DeckPresetItem("crunchyroll", "Crunchyroll", "Animes e Series", "video", "orange"),
    DeckPresetItem("terminal", "Terminal", "Linha de Comando", "terminal", "graphite"),
    DeckPresetItem("calculator", "Calculadora", "Utilitario", "calc", "slate"),
    DeckPresetItem("valorant_spike", "Spike Companion", "Temporizador Tático Valorant", "bomb", "ruby"),
)

@OptIn(ExperimentalLayoutApi::class)
@Composable
fun DeckAddTileDialog(
    onDismiss: () -> Unit,
    onAddPreset: (presetId: String) -> Unit,
    onAddCustom: (name: String, command: String) -> Unit,
) {
    var isCustomTab by remember { mutableStateOf(false) }
    var customName by remember { mutableStateOf("") }
    var customCommand by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Text(
                text = "Adicionar Atalho ao Stream Deck",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.SemiBold,
            )
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(14.dp),
            ) {
                Text(
                    text = "Escolha um aplicativo recomendado ou defina um comando customizado para executar no computador.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    FilledTonalButton(
                        onClick = { isCustomTab = false },
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = if (!isCustomTab) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                            contentColor = if (!isCustomTab) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurface,
                        ),
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(vertical = 8.dp),
                    ) {
                        Text("Recomendados", style = MaterialTheme.typography.labelLarge)
                    }

                    FilledTonalButton(
                        onClick = { isCustomTab = true },
                        colors = ButtonDefaults.filledTonalButtonColors(
                            containerColor = if (isCustomTab) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceContainerHigh,
                            contentColor = if (isCustomTab) MaterialTheme.colorScheme.onPrimaryContainer else MaterialTheme.colorScheme.onSurface,
                        ),
                        modifier = Modifier.weight(1f),
                        contentPadding = PaddingValues(vertical = 8.dp),
                    ) {
                        Text("Customizado", style = MaterialTheme.typography.labelLarge)
                    }
                }

                if (!isCustomTab) {
                    FlowRow(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        DECK_PRESET_LIST.forEach { preset ->
                            Surface(
                                shape = RoundedCornerShape(12.dp),
                                color = MaterialTheme.colorScheme.surfaceContainerHigh,
                                border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant),
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable {
                                        onAddPreset(preset.id)
                                        onDismiss()
                                    },
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(horizontal = 14.dp, vertical = 10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = preset.name,
                                            style = MaterialTheme.typography.titleMedium,
                                            fontWeight = FontWeight.SemiBold,
                                        )
                                        Text(
                                            text = preset.subtitle,
                                            style = MaterialTheme.typography.bodySmall,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                    Spacer(Modifier.width(8.dp))
                                    FilledTonalButton(
                                        onClick = {
                                            onAddPreset(preset.id)
                                            onDismiss()
                                        },
                                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 6.dp),
                                    ) {
                                        Text("+ Adicionar", style = MaterialTheme.typography.labelMedium)
                                    }
                                }
                            }
                        }
                    }
                } else {
                    Column(
                        modifier = Modifier.fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        OutlinedTextField(
                            value = customName,
                            onValueChange = { customName = it },
                            label = { Text("Nome do Botao") },
                            placeholder = { Text("Ex: Meu Jogo, OBS Replay") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                        )

                        OutlinedTextField(
                            value = customCommand,
                            onValueChange = { customCommand = it },
                            label = { Text("Comando ou URL no PC") },
                            placeholder = { Text("Ex: obs, spotify, https://twitch.tv") },
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth(),
                        )

                        FilledTonalButton(
                            onClick = {
                                if (customName.isNotBlank() && customCommand.isNotBlank()) {
                                    onAddCustom(customName.trim(), customCommand.trim())
                                    onDismiss()
                                }
                            },
                            enabled = customName.isNotBlank() && customCommand.isNotBlank(),
                            modifier = Modifier.fillMaxWidth(),
                            contentPadding = PaddingValues(vertical = 12.dp),
                        ) {
                            Text("Criar Botao", style = MaterialTheme.typography.labelLarge)
                        }
                    }
                }
            }
        },
        confirmButton = {},
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Fechar", style = MaterialTheme.typography.labelLarge)
            }
        },
    )
}

