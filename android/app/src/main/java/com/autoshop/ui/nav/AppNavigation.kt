package com.autoshop.ui.nav

import android.content.Intent
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Divider
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.ListItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.autoshop.data.model.Customer
import com.autoshop.data.model.Vehicle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.autoshop.RecordingActivity
import com.autoshop.data.network.AuthApi
import com.autoshop.data.network.CustomersApi
import com.autoshop.data.network.MessagesApi
import com.autoshop.data.storage.TokenStore
import com.autoshop.ui.assistant.AssistantScreen
import com.autoshop.ui.auth.LoginScreen
import com.autoshop.ui.customers.CustomerListScreen
import com.autoshop.ui.customers.ReportDetailScreen
import com.autoshop.ui.customers.VehicleDetailScreen
import com.autoshop.ui.customers.VehicleListScreen
import com.autoshop.ui.profile.ProfileScreen

sealed class Screen(val route: String) {
    object Login : Screen("login")
    object CustomerList : Screen("customers")
    object VehicleList : Screen("customers/{customerId}/vehicles") {
        fun forCustomer(customerId: String) = "customers/$customerId/vehicles"
    }
    object VehicleDetail : Screen("vehicles/{vehicleId}") {
        fun forVehicle(vehicleId: String) = "vehicles/$vehicleId"
    }
    object ReportDetail : Screen("reports/{reportId}?vehicleLabel={vehicleLabel}") {
        fun forReport(reportId: String, vehicleLabel: String) =
            "reports/$reportId?vehicleLabel=${android.net.Uri.encode(vehicleLabel)}"
    }
    object Assistant : Screen("assistant")
    object Inspect : Screen("inspect")
    object Profile : Screen("profile")
}

private data class TabItem(
    val screen: Screen,
    val label: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

private val bottomTabs = listOf(
    TabItem(Screen.CustomerList, "Customers", Icons.Filled.Person),
    TabItem(Screen.Assistant,    "Assistant", Icons.Filled.Email),
    TabItem(Screen.Inspect,      "Inspect",   Icons.Filled.CameraAlt),
    TabItem(Screen.Profile,      "Profile",   Icons.Filled.AccountCircle),
)

@Composable
fun AppNavigation(
    tokenStore: TokenStore,
    authApi: AuthApi,
    customersApi: CustomersApi,
    messagesApi: MessagesApi,
) {
    val navController = rememberNavController()
    val startDestination = if (tokenStore.getToken() != null) Screen.CustomerList.route
                           else Screen.Login.route

    val isLoggedIn by tokenStore.isLoggedIn.collectAsState()
    LaunchedEffect(isLoggedIn) {
        if (!isLoggedIn && navController.currentDestination?.route != Screen.Login.route) {
            navController.navigate(Screen.Login.route) {
                popUpTo(0) { inclusive = true }
            }
        }
    }

    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination
    val showBottomBar = bottomTabs.any { tab ->
        currentDestination?.hierarchy?.any { it.route == tab.screen.route } == true
    }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomTabs.forEach { tab ->
                        val selected = currentDestination?.hierarchy
                            ?.any { it.route == tab.screen.route } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(tab.screen.route) {
                                    popUpTo(navController.graph.findStartDestination().id) {
                                        saveState = true
                                    }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(tab.icon, contentDescription = tab.label) },
                            label = { Text(tab.label) },
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = startDestination,
            modifier = Modifier.padding(innerPadding),
        ) {
            composable(Screen.Login.route) {
                LoginScreen(
                    tokenStore = tokenStore,
                    authApi = authApi,
                    onLoginSuccess = {
                        navController.navigate(Screen.CustomerList.route) {
                            popUpTo(Screen.Login.route) { inclusive = true }
                        }
                    },
                )
            }

            composable(Screen.CustomerList.route) {
                CustomerListScreen(
                    customersApi = customersApi,
                    onCustomerClick = { customerId ->
                        navController.navigate(Screen.VehicleList.forCustomer(customerId))
                    },
                )
            }

            composable(
                route = Screen.VehicleList.route,
                arguments = listOf(navArgument("customerId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val customerId = backStackEntry.arguments?.getString("customerId") ?: return@composable
                VehicleListScreen(
                    customerId = customerId,
                    customersApi = customersApi,
                    onVehicleClick = { vehicleId ->
                        navController.navigate(Screen.VehicleDetail.forVehicle(vehicleId))
                    },
                    onBack = { navController.popBackStack() },
                )
            }

            composable(
                route = Screen.VehicleDetail.route,
                arguments = listOf(navArgument("vehicleId") { type = NavType.StringType }),
            ) { backStackEntry ->
                val vehicleId = backStackEntry.arguments?.getString("vehicleId") ?: return@composable
                VehicleDetailScreen(
                    vehicleId = vehicleId,
                    messagesApi = messagesApi,
                    onBack = { navController.popBackStack() },
                    onReportClick = { reportId, vehicleLabel ->
                        navController.navigate(Screen.ReportDetail.forReport(reportId, vehicleLabel))
                    },
                )
            }

            composable(
                route = Screen.ReportDetail.route,
                arguments = listOf(
                    navArgument("reportId") { type = NavType.StringType },
                    navArgument("vehicleLabel") { type = NavType.StringType; defaultValue = "" },
                ),
            ) { backStackEntry ->
                val reportId = backStackEntry.arguments?.getString("reportId") ?: return@composable
                val vehicleLabel = backStackEntry.arguments?.getString("vehicleLabel") ?: ""
                ReportDetailScreen(
                    reportId = reportId,
                    vehicleLabel = vehicleLabel,
                    messagesApi = messagesApi,
                    onBack = { navController.popBackStack() },
                )
            }

            composable(Screen.Assistant.route) {
                AssistantScreen(messagesApi = messagesApi)
            }

            composable(Screen.Inspect.route) {
                InspectScreen(tokenStore = tokenStore, customersApi = customersApi)
            }

            composable(Screen.Profile.route) {
                ProfileScreen(
                    tokenStore = tokenStore,
                    onLogout = {
                        navController.navigate(Screen.Login.route) {
                            popUpTo(0) { inclusive = true }
                        }
                    },
                )
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun InspectScreen(tokenStore: TokenStore, customersApi: CustomersApi) {
    val context = LocalContext.current
    var customers by remember { mutableStateOf<List<Customer>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var selectedCustomer by remember { mutableStateOf<Customer?>(null) }
    var vehicles by remember { mutableStateOf<List<Vehicle>>(emptyList()) }
    var vehiclesLoading by remember { mutableStateOf(false) }

    LaunchedEffect(Unit) {
        try {
            val response = customersApi.listCustomers()
            if (response.isSuccessful) customers = response.body() ?: emptyList()
            else errorMessage = "Failed to load customers (HTTP ${response.code()})."
        } catch (e: Exception) {
            errorMessage = "Network error: ${e.message}"
        } finally {
            isLoading = false
        }
    }

    LaunchedEffect(selectedCustomer) {
        val customer = selectedCustomer ?: return@LaunchedEffect
        vehiclesLoading = true
        vehicles = emptyList()
        try {
            val response = customersApi.listVehicles(customer.customerId)
            if (response.isSuccessful) vehicles = response.body() ?: emptyList()
        } catch (_: Exception) {}
        vehiclesLoading = false
    }

    val shopId = tokenStore.getShopId()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(if (selectedCustomer == null) "Select Customer" else selectedCustomer!!.name) },
                navigationIcon = {
                    if (selectedCustomer != null) {
                        IconButton(onClick = { selectedCustomer = null }) {
                            Icon(Icons.Filled.ArrowBack, contentDescription = "Back")
                        }
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
                    modifier = Modifier.align(Alignment.Center).padding(16.dp),
                )
                selectedCustomer == null -> LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(customers, key = { it.customerId }) { customer ->
                        ListItem(
                            headlineContent = { Text(customer.name) },
                            supportingContent = {
                                Text(listOfNotNull(customer.email, customer.phone).joinToString(" · ").ifEmpty { "No contact info" })
                            },
                            leadingContent = { Icon(Icons.Filled.Person, contentDescription = null) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { selectedCustomer = customer },
                        )
                        Divider()
                    }
                }
                vehiclesLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                vehicles.isEmpty() -> Text(
                    text = "No vehicles for ${selectedCustomer!!.name}.",
                    modifier = Modifier.align(Alignment.Center).padding(16.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                else -> LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(vehicles, key = { it.vehicleId }) { vehicle ->
                        ListItem(
                            headlineContent = { Text("${vehicle.year} ${vehicle.make} ${vehicle.model}") },
                            supportingContent = vehicle.trim?.let { { Text(it) } },
                            leadingContent = { Icon(Icons.Filled.DirectionsCar, contentDescription = null) },
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    val intent = Intent(context, RecordingActivity::class.java).apply {
                                        putExtra("SHOP_ID", shopId)
                                        putExtra("VEHICLE_ID", vehicle.vehicleId)
                                        putExtra("CUSTOMER_NAME", selectedCustomer!!.name)
                                    }
                                    context.startActivity(intent)
                                },
                        )
                        Divider()
                    }
                }
            }
        }
    }
}
