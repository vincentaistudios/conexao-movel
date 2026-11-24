// SPDX-License-Identifier: GPL-3.0-or-later
package app.nectarlink.android.ui.deck

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.size
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.StrokeJoin
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp

@Composable
fun SpikeIcon(
    color: Color,
    size: Dp = 28.dp,
    modifier: Modifier = Modifier,
) {
    val path = remember { Path() }
    Canvas(modifier = modifier.size(size)) {
        val w = this.size.width
        val h = this.size.height
        val stroke = Stroke(width = w * 0.08f, cap = StrokeCap.Round, join = StrokeJoin.Round)

        // Corpo piramidal superior da Spike
        path.rewind()
        path.moveTo(w * 0.5f, h * 0.12f)
        path.lineTo(w * 0.85f, h * 0.65f)
        path.lineTo(w * 0.15f, h * 0.65f)
        path.close()
        drawPath(path, color = color, style = stroke)

        // Núcleo interno de radianita
        drawCircle(
            color = color,
            radius = w * 0.12f,
            center = Offset(w * 0.5f, h * 0.45f),
            style = Fill,
        )

        // Hastes de ancoragem da base
        drawLine(color, Offset(w * 0.35f, h * 0.65f), Offset(w * 0.25f, h * 0.88f), strokeWidth = stroke.width)
        drawLine(color, Offset(w * 0.5f, h * 0.65f), Offset(w * 0.5f, h * 0.92f), strokeWidth = stroke.width)
        drawLine(color, Offset(w * 0.65f, h * 0.65f), Offset(w * 0.75f, h * 0.88f), strokeWidth = stroke.width)
    }
}

@Composable
fun SpikeExplosionIcon(
    color: Color,
    size: Dp = 32.dp,
    modifier: Modifier = Modifier,
) {
    val path = remember { Path() }
    Canvas(modifier = modifier.size(size)) {
        val w = this.size.width
        val h = this.size.height
        val cx = w * 0.5f
        val cy = h * 0.5f
        val stroke = Stroke(width = w * 0.08f, cap = StrokeCap.Round, join = StrokeJoin.Round)

        // Estrela de impacto / onda de choque tática
        path.rewind()
        val numPoints = 8
        val outerRadius = w * 0.46f
        val innerRadius = w * 0.22f

        for (i in 0 until (numPoints * 2)) {
            val radius = if (i % 2 == 0) outerRadius else innerRadius
            val angle = (i * Math.PI / numPoints) - (Math.PI / 2.0)
            val x = cx + (radius * Math.cos(angle)).toFloat()
            val y = cy + (radius * Math.sin(angle)).toFloat()
            if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
        }
        path.close()

        drawPath(path, color = color, style = Fill)
        drawPath(path, color = Color.White.copy(alpha = 0.8f), style = stroke)
    }
}

@Composable
fun DefuseShieldIcon(
    color: Color,
    size: Dp = 24.dp,
    modifier: Modifier = Modifier,
) {
    val path = remember { Path() }
    Canvas(modifier = modifier.size(size)) {
        val w = this.size.width
        val h = this.size.height
        val stroke = Stroke(width = w * 0.09f, cap = StrokeCap.Round, join = StrokeJoin.Round)

        path.rewind()
        path.moveTo(w * 0.5f, h * 0.1f)
        path.lineTo(w * 0.88f, h * 0.24f)
        path.lineTo(w * 0.88f, h * 0.58f)
        path.cubicTo(w * 0.88f, h * 0.78f, w * 0.65f, h * 0.92f, w * 0.5f, h * 0.95f)
        path.cubicTo(w * 0.35f, h * 0.92f, w * 0.12f, h * 0.78f, w * 0.12f, h * 0.58f)
        path.lineTo(w * 0.12f, h * 0.24f)
        path.close()

        drawPath(path, color = color, style = stroke)

        // Barra de corte central (Half Checkpoint)
        drawLine(
            color = color,
            start = Offset(w * 0.5f, h * 0.28f),
            end = Offset(w * 0.5f, h * 0.75f),
            strokeWidth = stroke.width * 0.9f,
        )
    }
}

