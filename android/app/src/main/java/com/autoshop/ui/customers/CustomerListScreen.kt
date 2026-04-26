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
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Person
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
import com.autoshop.data.model.CreateCustomerRequest
import com.autoshop.data.model.Customer
import com.autoshop.data.network.CustomersApi
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CustomerListScreen(
    customersApi: CustomersApi,
    onCustomerClick: (customerId: String) -> Unit,
) {
    var customers by remember { mutableStateOf<List<Customer>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var showCreateDialog by remember { mutableStateOf(false) }
    var createError by remember { mutableStateOf<String?>(null) }
    val scope = rememberCoroutineScope()

    fun loadCustomers() {
        scope.launch {
            isLoading = true
            errorMessage = null
            try {
                val response = customersApi.listCustomers()
                if (response.isSuccessful) {
                    customers = response.body() ?: emptyList()
                } else {
                    errorMessage = "Failed to load customers (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                errorMessage = "Network error: ${e.message}"
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) { loadCustomers() }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Customers") })
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showCreateDialog = true }) {
                Icon(Icons.Filled.Add, contentDescription = "Add customer")
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
                customers.isEmpty() -> Text(
                    text = "No customers yet. Tap + to add one.",
                    modifier = Modifier
                        .align(Alignment.Center)
                        .padding(16.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(customers, key = { it.customerId }) { customer ->
                        ListItem(
                            headlineContent = { Text(customer.name) },
                            supportingContent = {
                                Text(
                                    listOfNotNull(customer.email, customer.phone)
                                        .joinToString(" · ")
                                        .ifEmpty { "No contact info" }
                                )
                            },
                            leadingContent = {
                                Icon(Icons.Filled.Person, contentDescription = null)
                            },
                            trailingContent = {
                                IconButton(onClick = {
                                    scope.launch {
                                        try {
                                            customersApi.deleteCustomer(customer.customerId)
                                            loadCustomers()
                                        } catch (e: Exception) {
                                            errorMessage = "Delete failed: ${e.message}"
                                        }
                                    }
                                }) {
                                    Icon(
                                        Icons.Filled.Delete,
                                        contentDescription = "Delete ${customer.name}",
                                        tint = MaterialTheme.colorScheme.error,
                                    )
                                }
                            },
                            modifier = Modifier.clickable { onCustomerClick(customer.customerId) },
                        )
                        Divider()
                    }
                }
            }
        }
    }

    if (showCreateDialog) {
        CreateCustomerDialog(
            error = createError,
            onDismiss = {
                showCreateDialog = false
                createError = null
            },
            onCreate = { name, email, phone ->
                scope.launch {
                    isLoading = true
                    try {
                        customersApi.createCustomer(
                            CreateCustomerRequest(
                                name = name,
                                email = email.ifBlank { null },
                                phone = phone.ifBlank { null },
                            )
                        )
                        showCreateDialog = false
                        createError = null
                        loadCustomers()
                    } catch (e: Exception) {
                        createError = "Create failed: ${e.message}"
                        isLoading = false
                    }
                }
            },
        )
    }
}

@Composable
private fun CreateCustomerDialog(
    error: String?,
    onDismiss: () -> Unit,
    onCreate: (name: String, email: String, phone: String) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var email by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var nameError by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("New Customer") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it; nameError = false },
                    label = { Text("Name *") },
                    isError = nameError,
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                    modifier = Modifier.fillMaxWidth(),
                )
                if (nameError) {
                    Text(
                        "Name is required.",
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
                OutlinedTextField(
                    value = email,
                    onValueChange = { email = it },
                    label = { Text("Email") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Email,
                        imeAction = ImeAction.Next,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    value = phone,
                    onValueChange = { phone = it },
                    label = { Text("Phone") },
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(
                        keyboardType = KeyboardType.Phone,
                        imeAction = ImeAction.Done,
                    ),
                    modifier = Modifier.fillMaxWidth(),
                )
                if (error != null) {
                    Text(
                        text = error,
                        color = MaterialTheme.colorScheme.error,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                if (name.isBlank()) { nameError = true; return@TextButton }
                onCreate(name.trim(), email.trim(), phone.trim())
            }) {
                Text("Create")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Cancel") }
        },
    )
}
