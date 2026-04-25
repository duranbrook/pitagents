package com.autoshop.ui.nav

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.autoshop.data.network.AuthApi
import com.autoshop.data.network.CustomersApi
import com.autoshop.data.network.MessagesApi
import com.autoshop.data.storage.TokenStore
import com.autoshop.ui.assistant.AssistantScreen
import com.autoshop.ui.auth.LoginScreen
import com.autoshop.ui.customers.CustomerListScreen
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
    object Assistant : Screen("assistant")
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
                )
            }

            composable(Screen.Assistant.route) {
                AssistantScreen(messagesApi = messagesApi)
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
