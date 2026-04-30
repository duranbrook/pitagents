package com.autoshop.ui.customers

import android.content.Intent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Share
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.autoshop.data.model.ReportDetail
import com.autoshop.data.model.ReportEstimateItem
import com.autoshop.data.model.ReportFinding
import com.autoshop.data.network.MessagesApi
import kotlinx.coroutines.launch

private const val BACKEND_BASE_URL = "https://backend-production-5320.up.railway.app"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ReportDetailScreen(
    reportId: String,
    vehicleLabel: String,
    messagesApi: MessagesApi,
    onBack: () -> Unit,
) {
    var report by remember { mutableStateOf<ReportDetail?>(null) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()
    val context = LocalContext.current

    LaunchedEffect(reportId) {
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                val response = messagesApi.getReport(reportId)
                if (response.isSuccessful) {
                    report = response.body()
                } else {
                    errorMessage = "Failed to load report (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                errorMessage = "Network error: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(vehicleLabel.ifBlank { "Report" }) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding),
        ) {
            when {
                isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                errorMessage != null -> Text(
                    text = errorMessage!!,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(16.dp),
                )
                report != null -> ReportDetailContent(
                    report = report!!,
                    onShare = {
                        val shareUrl = "$BACKEND_BASE_URL/r/${report!!.shareToken}"
                        val intent = Intent(Intent.ACTION_SEND).apply {
                            type = "text/plain"
                            putExtra(Intent.EXTRA_TEXT, shareUrl)
                            putExtra(Intent.EXTRA_SUBJECT, "Inspection Report")
                        }
                        context.startActivity(Intent.createChooser(intent, "Share Report"))
                    },
                )
            }
        }
    }
}

@Composable
private fun ReportDetailContent(
    report: ReportDetail,
    onShare: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        // Vehicle card
        report.vehicle?.let { vehicle ->
            VehicleInfoCard(vehicle = vehicle)
        }

        // Summary section
        report.summary?.let { summary ->
            SectionCard(title = "Summary") {
                Text(
                    text = summary,
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface,
                )
            }
        }

        // Inspection findings
        if (report.findings.isNotEmpty()) {
            SectionCard(title = "Inspection Findings") {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    report.findings.forEachIndexed { index, finding ->
                        FindingRow(finding = finding)
                        if (index < report.findings.size - 1) {
                            Divider(color = MaterialTheme.colorScheme.outlineVariant)
                        }
                    }
                }
            }
        }

        // Estimate table
        if (report.estimate.isNotEmpty()) {
            SectionCard(title = "Estimate") {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    // Header row
                    Row(modifier = Modifier.fillMaxWidth()) {
                        Text(
                            text = "Part",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.weight(1f),
                        )
                        Text(
                            text = "Labor",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.width(64.dp),
                        )
                        Text(
                            text = "Parts",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.width(64.dp),
                        )
                        Text(
                            text = "Total",
                            style = MaterialTheme.typography.labelMedium,
                            fontWeight = FontWeight.SemiBold,
                            modifier = Modifier.width(64.dp),
                        )
                    }

                    Divider(color = MaterialTheme.colorScheme.outline)

                    report.estimate.forEach { item ->
                        EstimateRow(item = item)
                    }

                    Divider(color = MaterialTheme.colorScheme.outline)

                    // Grand total
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                    ) {
                        Text(
                            text = "Grand Total",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                        )
                        Text(
                            text = "${"$%.2f".format(report.total)}",
                            style = MaterialTheme.typography.titleSmall,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                }
            }
        }

        // Share button
        Button(
            onClick = onShare,
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(
                containerColor = MaterialTheme.colorScheme.primary,
            ),
        ) {
            Icon(Icons.Filled.Share, contentDescription = null)
            Spacer(modifier = Modifier.width(8.dp))
            Text("Share Report")
        }

        Spacer(modifier = Modifier.height(16.dp))
    }
}

@Composable
private fun VehicleInfoCard(vehicle: com.autoshop.data.model.ReportVehicle) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer,
        ),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "Vehicle",
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f),
            )
            Spacer(modifier = Modifier.height(4.dp))
            val yearMakeModel = listOfNotNull(
                vehicle.year?.toString(),
                vehicle.make,
                vehicle.model,
                vehicle.trim,
            ).joinToString(" ")
            if (yearMakeModel.isNotBlank()) {
                Text(
                    text = yearMakeModel,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onPrimaryContainer,
                )
            }
            vehicle.vin?.let { vin ->
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "VIN: $vin",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onPrimaryContainer.copy(alpha = 0.7f),
                )
            }
        }
    }
}

@Composable
private fun SectionCard(
    title: String,
    content: @Composable () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = title,
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.primary,
            )
            Spacer(modifier = Modifier.height(12.dp))
            content()
        }
    }
}

@Composable
private fun FindingRow(finding: ReportFinding) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
    ) {
        // Severity icon
        val (severityEmoji, severityColor) = when (finding.severity.lowercase()) {
            "high", "urgent", "critical" -> Pair(
                "🔴",
                MaterialTheme.colorScheme.error,
            )
            "medium", "moderate" -> Pair(
                "🟡",
                MaterialTheme.colorScheme.tertiary,
            )
            else -> Pair(
                "🟢",
                MaterialTheme.colorScheme.primary,
            )
        }

        Text(
            text = severityEmoji,
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(end = 8.dp, top = 2.dp),
        )

        Column(modifier = Modifier.weight(1f)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = finding.part,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.weight(1f),
                )
                Spacer(modifier = Modifier.width(8.dp))
                // Severity badge chip
                Box(
                    modifier = Modifier
                        .background(
                            color = severityColor.copy(alpha = 0.15f),
                            shape = RoundedCornerShape(4.dp),
                        )
                        .padding(horizontal = 6.dp, vertical = 2.dp),
                ) {
                    Text(
                        text = finding.severity.uppercase(),
                        style = MaterialTheme.typography.labelSmall,
                        color = severityColor,
                        fontWeight = FontWeight.SemiBold,
                    )
                }
            }
            if (finding.notes.isNotBlank()) {
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = finding.notes,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

@Composable
private fun EstimateRow(item: ReportEstimateItem) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        verticalAlignment = Alignment.Top,
    ) {
        Text(
            text = item.part,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.weight(1f),
        )
        Text(
            text = "${"$%.0f".format(item.laborCost)}",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.width(64.dp),
        )
        Text(
            text = "${"$%.0f".format(item.partsCost)}",
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.width(64.dp),
        )
        Text(
            text = "${"$%.0f".format(item.total)}",
            style = MaterialTheme.typography.bodySmall,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.width(64.dp),
        )
    }
}
