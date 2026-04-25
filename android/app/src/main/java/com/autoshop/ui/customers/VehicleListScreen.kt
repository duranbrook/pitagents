package com.autoshop.ui.customers

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.autoshop.data.model.CreateVehicleRequest
import com.autoshop.data.model.Vehicle
import com.autoshop.data.network.CustomersApi
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VehicleListScreen(
    customerId: String,
    customersApi: CustomersApi,
    onVehicleClick: (vehicleId: String) -> Unit,
    onBack: () -> Unit,
) {
    var vehicles by remember { mutableStateOf<List<Vehicle>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var showCreateDialog by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    fun loadVehicles() {
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                val response = customersApi.listVehicles(customerId)
                if (response.isSuccessful) {
                    vehicles = response.body() ?: emptyList()
                } else {
                    errorMessage = "Failed to load vehicles (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                errorMessage = "Network error: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(customerId) { loadVehicles() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Vehicles") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Icon(Icons.Filled.Add, contentDescription = "Add vehicle")
            }
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
                vehicles.isEmpty() -> Text(
                    text = "No vehicles yet. Tap + to add one.",
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(16.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(vehicles, key = { it.vehicleId }) { vehicle ->
                        ListItem(
                            headlineContent = {
                                Text("${vehicle.year} ${vehicle.make} ${vehicle.model}")
                            },
                            supportingContent = {
                                Text(
                                    listOfNotNull(vehicle.trim, vehicle.color, vehicle.vin)
                                        .joinToString(" · ")
                                        .ifEmpty { "No additional info" }
                                )
                            },
                            leadingContent = {
                                Icon(Icons.Filled.DirectionsCar, contentDescription = null)
                            },
                            trailingContent = {
                                IconButton(onClick = {
                                    scope.launch {
                                        try {
                                            customersApi.deleteVehicle(vehicle.vehicleId)
                                            loadVehicles()
                                        } catch (e: Exception) {
                                            errorMessage = "Delete failed: ${e.message}"
                                        }
                                    }
                                }) {
                                    Icon(
                                        Icons.Filled.Delete,
                                        contentDescription = "Delete vehicle",
                                        tint = MaterialTheme.colorScheme.error,
                                    )
                                }
                            },
                            modifier = Modifier.clickable { onVehicleClick(vehicle.vehicleId) },
                        )
                        Divider()
                    }
                }
            }
        }
    }

    if (showCreateDialog) {
        CreateVehicleDialog(
            onDismiss = { showCreateDialog = false },
            onCreate = { year, make, model, trim, vin, color ->
                scope.launch {
                    showCreateDialog = false
                    isLoading = true
                    try {
                        customersApi.createVehicle(
                            customerId,
                            CreateVehicleRequest(
                                year = year,
                                make = make,
                                model = model,
                                trim = trim.ifBlank { null },
                                vin = vin.ifBlank { null },
                                color = color.ifBlank { null },
                            ),
                        )
                        loadVehicles()
                    } catch (e: Exception) {
                        errorMessage = "Create failed: ${e.message}"
                        isLoading = false
                    }
                }
            },
        )
    }
}

@Composable
private fun CreateVehicleDialog(
    onDismiss: () -> Unit,
    onCreate: (year: Int, make: String, model: String, trim: String, vin: String, color: String) -> Unit,
) {
    var yearText by remember { mutableStateOf("") }
    var make by remember { mutableStateOf("") }
    var model by remember { mutableStateOf("") }
    var trim by remember { mutableStateOf("") }
    var vin by remember { mutableStateOf("") }
    var color by remember { mutableStateOf("") }
    var validationError by remember { mutableStateOf<String?>(null) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Add Vehicle") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                validationError?.let { err ->
                    Text(err, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.labelSmall)
                }
                OutlinedTextField(
                    value = yearText,
                    onValueChange = { yearText = it; validationError = null },
                    label = { Text("Year *") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number, imeAction = ImeAction.Next),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = make,
                    onValueChange = { make = it; validationError = null },
                    label = { Text("Make *") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = model,
                    onValueChange = { model = it; validationError = null },
                    label = { Text("Model *") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = trim,
                    onValueChange = { trim = it },
                    label = { Text("Trim") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = vin,
                    onValueChange = { vin = it },
                    label = { Text("VIN") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = color,
                    onValueChange = { color = it },
                    label = { Text("Color") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Done),
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val year = yearText.toIntOrNull()
                when {
                    year == null -> validationError = "Year must be a number."
                    make.isBlank() -> validationError = "Make is required."
                    model.isBlank() -> validationError = "Model is required."
                    else -> onCreate(year, make.trim(), model.trim(), trim.trim(), vin.trim(), color.trim())
                }
            }) {
                Text("Add")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        },
    )
}
