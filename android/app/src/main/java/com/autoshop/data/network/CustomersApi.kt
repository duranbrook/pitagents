package com.autoshop.data.network

import com.autoshop.data.model.CreateCustomerRequest
import com.autoshop.data.model.CreateVehicleRequest
import com.autoshop.data.model.Customer
import com.autoshop.data.model.Vehicle
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface CustomersApi {

    @GET("customers")
    suspend fun listCustomers(): Response<List<Customer>>

    @POST("customers")
    suspend fun createCustomer(@Body request: CreateCustomerRequest): Response<Customer>

    @DELETE("customers/{id}")
    suspend fun deleteCustomer(@Path("id") customerId: String): Response<Unit>

    @GET("customers/{id}/vehicles")
    suspend fun listVehicles(@Path("id") customerId: String): Response<List<Vehicle>>

    @POST("customers/{id}/vehicles")
    suspend fun createVehicle(
        @Path("id") customerId: String,
        @Body request: CreateVehicleRequest,
    ): Response<Vehicle>

    @DELETE("vehicles/{id}")
    suspend fun deleteVehicle(@Path("id") vehicleId: String): Response<Unit>
}
