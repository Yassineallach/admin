@file:OptIn(ExperimentalLayoutApi::class, ExperimentalMaterial3Api::class)

package com.opengenerativeai.imagestudio.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.opengenerativeai.imagestudio.data.ModelParam
import com.opengenerativeai.imagestudio.data.ParamKind
import kotlin.math.roundToInt

/** Renders one control per model parameter, driven by the catalog schema. */
@Composable
fun ParamControls(
    params: List<ModelParam>,
    values: Map<String, Any>,
    onChange: (String, Any?) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(14.dp)) {
        params.forEach { p ->
            when (p.kind) {
                ParamKind.ENUM -> EnumControl(p, values[p.name], onChange)
                ParamKind.INT, ParamKind.FLOAT -> NumberControl(p, values[p.name], onChange)
                ParamKind.BOOL -> Row(verticalAlignment = Alignment.CenterVertically) {
                    Label(p.title, Modifier.weight(1f))
                    Switch(
                        checked = values[p.name] as? Boolean ?: false,
                        onCheckedChange = { onChange(p.name, it) },
                    )
                }
                ParamKind.TEXT -> OutlinedTextField(
                    value = values[p.name] as? String ?: "",
                    onValueChange = { onChange(p.name, it.ifEmpty { null }) },
                    label = { Text(p.title) },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

@Composable
private fun Label(text: String, modifier: Modifier = Modifier) {
    Text(text, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant, modifier = modifier)
}

@Composable
private fun EnumControl(p: ModelParam, value: Any?, onChange: (String, Any?) -> Unit) {
    // Long lists (effect names, upscaler models) read better as a dropdown than as chips.
    if (p.values.size > 12) {
        var expanded by remember { mutableStateOf(false) }
        ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
            OutlinedTextField(
                value = value?.toString() ?: "Default",
                onValueChange = {},
                readOnly = true,
                label = { Text(p.title) },
                trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
                modifier = Modifier.fillMaxWidth().menuAnchor(MenuAnchorType.PrimaryNotEditable),
            )
            ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                p.values.forEach { v ->
                    DropdownMenuItem(
                        text = { Text(v.toString()) },
                        onClick = { onChange(p.name, v); expanded = false },
                    )
                }
            }
        }
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Label(p.title)
        FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            p.values.forEach { v ->
                val selected = value?.toString() == v.toString()
                FilterChip(
                    selected = selected,
                    // Re-tapping an optional choice clears it so the API default applies.
                    onClick = { onChange(p.name, if (selected && p.default == null) null else v) },
                    label = { Text(v.toString()) },
                )
            }
        }
    }
}

@Composable
private fun NumberControl(p: ModelParam, value: Any?, onChange: (String, Any?) -> Unit) {
    val isInt = p.kind == ParamKind.INT
    val min = p.min
    val max = p.max
    if (min != null && max != null && max > min && p.default != null) {
        val current = (value as? Number)?.toDouble() ?: min
        Column {
            Row {
                Label(p.title, Modifier.weight(1f))
                Text(format(current, isInt), style = MaterialTheme.typography.labelLarge)
            }
            val count = ((max - min) / p.step).roundToInt()
            Slider(
                value = current.toFloat(),
                onValueChange = { raw ->
                    val snapped = min + ((raw - min) / p.step).roundToInt() * p.step
                    val clamped = snapped.coerceIn(min, max)
                    onChange(p.name, if (isInt) clamped.roundToInt() else round(clamped, p.step))
                },
                valueRange = min.toFloat()..max.toFloat(),
                steps = if (count in 2..200) count - 1 else 0,
            )
        }
        return
    }
    // No usable range or no default (seed, sharpen…): a free-form field, blank means unset.
    var text by remember(p.name) { mutableStateOf(value?.let { format((it as Number).toDouble(), isInt) } ?: "") }
    val hint = if (min != null && max != null) "${format(min, isInt)} – ${format(max, isInt)}" else "Optional"
    OutlinedTextField(
        value = text,
        onValueChange = { input ->
            text = input
            val parsed: Any? = if (isInt) input.toIntOrNull() else input.toDoubleOrNull()
            onChange(p.name, parsed)
        },
        label = { Text(p.title) },
        placeholder = { Text(hint) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = if (isInt) KeyboardType.Number else KeyboardType.Decimal),
        modifier = Modifier.fillMaxWidth(),
    )
}

private fun format(v: Double, isInt: Boolean) =
    if (isInt || v == v.roundToInt().toDouble()) v.roundToInt().toString() else "%.2f".format(v)

private fun round(v: Double, step: Double): Double {
    val decimals = step.toBigDecimal().stripTrailingZeros().scale().coerceAtLeast(0)
    return v.toBigDecimal().setScale(decimals, java.math.RoundingMode.HALF_UP).toDouble()
}
