# Requirements Document

## Introduction

El Gestor de Inventario es un sistema que permite administrar productos en un almacén, incluyendo la gestión de cantidades, información de productos, y operaciones de entrada/salida de stock. El sistema utilizará FastAPI para exponer una API REST y permitirá persistencia en memoria inicialmente, con migración futura a DynamoDB.

## Glossary

- **Inventory_System**: El sistema completo que gestiona el inventario de productos
- **Product**: Un artículo en el inventario con identificador único, nombre, descripción, precio y cantidad en stock
- **Stock_Operation**: Una operación que modifica la cantidad de un producto (entrada o salida)
- **API_Client**: Aplicación o usuario que consume los endpoints de la API REST
- **In_Memory_Store**: Almacenamiento temporal de productos en memoria durante la ejecución
- **Product_ID**: Identificador único alfanumérico de un producto
- **Stock_Level**: Cantidad actual de unidades de un producto en inventario

## Requirements

### Requirement 1: Crear Productos

**User Story:** Como administrador del inventario, quiero crear nuevos productos en el sistema, para poder comenzar a gestionar su stock.

#### Acceptance Criteria

1. WHEN an API_Client sends a product creation request containing name, description, and price fields with valid values, THE Inventory_System SHALL create the Product in the In_Memory_Store and return a 201 status code with the created Product data including the assigned Product_ID
2. THE Inventory_System SHALL generate and assign a unique Product_ID of maximum 100 characters to each new Product
3. WHEN an API_Client sends a product creation request with missing required fields (name, description, or price), THE Inventory_System SHALL reject the request, validate that present fields contain meaningful values, and return a 400 status code with error details
4. WHEN an API_Client sends a product creation request with a name exceeding 200 characters, THE Inventory_System SHALL reject the request and return a 400 status code
5. WHEN an API_Client sends a product creation request with a description exceeding 500 characters, THE Inventory_System SHALL reject the request and return a 400 status code
6. THE Inventory_System SHALL initialize new Products with a Stock_Level of zero

### Requirement 2: Consultar Productos

**User Story:** Como usuario del sistema, quiero consultar información de productos, para conocer su disponibilidad y detalles.

#### Acceptance Criteria

1. WHEN an API_Client requests a Product by Product_ID that exists and has non-zero stock and non-zero price, THE Inventory_System SHALL return the complete Product information (Product_ID, name, description, price, Stock_Level) with a 200 status code within 2 seconds
2. WHEN an API_Client requests a Product by Product_ID that does not exist, THE Inventory_System SHALL return a 404 status code
3. WHEN an API_Client requests a Product by Product_ID that has zero stock or zero price, THE Inventory_System SHALL filter out the product and return a 404 status code
4. WHEN an API_Client requests the list of all products and the In_Memory_Store contains one or more Products with non-zero stock and non-zero price, THE Inventory_System SHALL return all qualifying Products in the In_Memory_Store with a 200 status code within 5 seconds
5. WHEN an API_Client requests the list of all products and the In_Memory_Store is initialized and contains zero Products, THE Inventory_System SHALL return an empty array with a 200 status code
6. WHEN an API_Client requests the list of all products and the In_Memory_Store is in an uninitialized state, THE Inventory_System SHALL return a 503 status code with an error message indicating the store is not ready
7. THE Inventory_System SHALL return product lists in a consistent JSON format with Product_ID, name, description, price, and Stock_Level

### Requirement 3: Actualizar Productos

**User Story:** Como administrador del inventario, quiero actualizar información de productos existentes, para mantener los datos correctos y actualizados.

#### Acceptance Criteria

1. WHEN an API_Client sends an update request for an existing Product with valid data for one or more updatable fields (name, description, price), THE Inventory_System SHALL update the specified fields and return a 200 status code with the updated Product
2. WHEN an API_Client sends an update request for a Product_ID that does not exist, THE Inventory_System SHALL return a 404 status code
3. WHEN an API_Client sends an update request with invalid data according to Requirement 7 validation rules, THE Inventory_System SHALL reject the request and return a 400 status code with error details as specified in Requirement 9
4. THE Inventory_System SHALL preserve the Product_ID during update operations
5. THE Inventory_System SHALL not allow Stock_Level to be updated through this operation
6. WHEN an API_Client sends an update request with no fields to update, THE Inventory_System SHALL reject the request and return a 400 status code
7. WHEN an API_Client sends an update request with one or more specified updatable fields (name, description, price) where the new values are identical to the current values, THE Inventory_System SHALL reject the request and return a 400 status code with an error message indicating no actual changes
8. WHEN an API_Client sends an update request with one or more specified updatable fields (name, description, price) where at least one new value differs from the current value, THE Inventory_System SHALL modify only the fields with different values and leave all other fields unchanged

### Requirement 4: Eliminar Productos

**User Story:** Como administrador del inventario, quiero eliminar productos del sistema, para mantener el catálogo limpio de productos discontinuados.

#### Acceptance Criteria

1. WHEN an API_Client sends a delete request for an existing Product, THE Inventory_System SHALL completely remove the Product from the In_Memory_Store and return a 204 status code
2. WHEN an API_Client sends a delete request for a Product_ID that does not exist in the In_Memory_Store, THE Inventory_System SHALL return a 404 status code
3. WHEN an API_Client sends a delete request for a Product that has already been deleted, THE Inventory_System SHALL return a 404 status code
4. WHEN an API_Client sends a delete request with an invalid Product_ID format according to Requirement 7 validation rules, THE Inventory_System SHALL return a 400 status code
5. WHEN an API_Client attempts to query a Product after a successful delete request, THE Inventory_System SHALL return a 404 status code

### Requirement 5: Gestionar Entradas de Stock

**User Story:** Como operador de almacén, quiero registrar entradas de productos al inventario, para incrementar el stock disponible.

#### Acceptance Criteria

1. WHEN an API_Client sends a stock addition request containing Product_ID and quantity fields with an existing Product_ID and quantity between 1 and 999999, THE Inventory_System SHALL increment the Stock_Level by the specified quantity and return a 200 status code
2. WHEN an API_Client sends a stock addition request for a Product_ID that does not exist, THE Inventory_System SHALL return a 404 status code
3. IF an API_Client sends a stock addition request with a quantity less than 1 or greater than 999999, THEN THE Inventory_System SHALL reject the request and return a 400 status code
4. IF an API_Client sends a stock addition request where the resulting Stock_Level would exceed 999999, THEN THE Inventory_System SHALL reject the request and return a 400 status code with an error message indicating maximum stock capacity exceeded
5. WHEN an API_Client successfully adds stock to a Product, THE Inventory_System SHALL return the updated Stock_Level equal to the original Stock_Level plus the added quantity
6. WHEN an API_Client sends a stock addition request with missing Product_ID or quantity fields, THE Inventory_System SHALL treat it as an invalid stock addition request and return a 400 status code

### Requirement 6: Gestionar Salidas de Stock

**User Story:** Como operador de almacén, quiero registrar salidas de productos del inventario, para reflejar ventas o consumo de stock.

#### Acceptance Criteria

1. WHEN an API_Client sends a stock removal request containing Product_ID and quantity fields with an existing Product_ID and quantity between 1 and 999999999 where the current Stock_Level is greater than or equal to the requested quantity, THE Inventory_System SHALL decrement the Stock_Level by the specified quantity and return a 200 status code with the updated Stock_Level
2. WHEN an API_Client sends a stock removal request for a Product_ID that does not exist, THE Inventory_System SHALL return a 404 status code
3. WHEN an API_Client sends a stock removal request with a quantity greater than the current Stock_Level, THE Inventory_System SHALL reject the entire request without removing any stock and return a 400 status code with error response formatted according to Requirement 9 containing an insufficient stock message
4. IF an API_Client sends a stock removal request with a quantity less than 1 or greater than 999999999, THEN THE Inventory_System SHALL reject the request and return a 400 status code
5. WHEN an API_Client sends a stock removal request with missing Product_ID or quantity fields, THE Inventory_System SHALL reject the request and return a 400 status code

### Requirement 7: Validar Datos de Entrada

**User Story:** Como desarrollador del sistema, quiero validar todos los datos de entrada, para garantizar la integridad de la información almacenada.

#### Acceptance Criteria

1. WHEN an API_Client sends a request with invalid JSON format, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code with an error message indicating JSON parse failure
2. WHEN an API_Client sends a request with a product name that is an empty string or exceeds 200 characters, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code with an error message indicating invalid name
3. WHEN an API_Client sends a request with a product description that exceeds 1000 characters, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code with an error message indicating invalid description
4. WHEN an API_Client sends a request with a product price that is negative or exceeds 999999999.99 or has more than 2 decimal places, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code with an error message indicating invalid price
5. WHEN an API_Client sends a request with a stock quantity that is negative or exceeds 2147483647, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code with an error message indicating invalid stock quantity
6. WHEN an API_Client sends a request with a Product_ID that is empty, exceeds 50 characters, or contains characters other than alphanumeric characters and hyphens, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code with an error message indicating invalid Product_ID format
7. WHEN an API_Client sends a request with a product name that is not a string type, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code
8. WHEN an API_Client sends a request with a product description that is not a string type, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code
9. WHEN an API_Client sends a request with a product price that is not a numeric type, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code
10. WHEN an API_Client sends a request with a stock quantity that is not an integer type, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code
11. WHEN an API_Client sends a request with a Product_ID that is not a string type, THE Inventory_System SHALL reject the request, block all further processing, log the rejection with timestamp and error details, and return a 400 status code

### Requirement 8: Consultar Disponibilidad de Stock

**User Story:** Como usuario del sistema, quiero consultar productos con stock disponible, para conocer qué productos están disponibles para venta.

#### Acceptance Criteria

1. WHEN an API_Client requests products with available stock, THE Inventory_System SHALL return all Products where Stock_Level is greater than zero in explicit product array format with a 200 status code
2. WHEN an API_Client requests products with low stock below a specified threshold between 1 and 10000 units, THE Inventory_System SHALL return all Products where Stock_Level is less than or equal to the threshold in explicit product array format with a 200 status code
3. WHEN an API_Client requests products with low stock without providing a threshold value, THE Inventory_System SHALL reject the request and return a 400 status code
4. WHEN an API_Client requests products with low stock with a threshold value outside the range of 1 to 10000 units, THE Inventory_System SHALL reject the request and return a 400 status code
5. WHEN the Inventory_System filters products by stock criteria and finds no matching Products, THE Inventory_System SHALL return an empty array with a 200 status code
6. THE Inventory_System SHALL return filtered product lists in the same JSON format as the complete product list

### Requirement 9: Manejo de Errores

**User Story:** Como desarrollador que integra con la API, quiero recibir mensajes de error descriptivos, para poder diagnosticar y corregir problemas rápidamente.

#### Acceptance Criteria

1. WHEN the Inventory_System encounters a validation error, THE Inventory_System SHALL return an error response in JSON format containing an "error_type" field with value "validation_error", a "message" field with a message between 10 and 200 characters, and an HTTP status code field
2. WHEN the Inventory_System encounters a resource not found error, THE Inventory_System SHALL return an error response in JSON format containing an "error_type" field with value "not_found", a "message" field with a message between 10 and 200 characters, and an HTTP status code field
3. WHEN the Inventory_System encounters a duplicate resource error, THE Inventory_System SHALL return an error response in JSON format containing an "error_type" field with value "conflict", a "message" field with a message between 10 and 200 characters, and an HTTP status code field
4. WHEN the Inventory_System encounters multiple validation errors in a single request, THE Inventory_System SHALL return an error response containing all validation errors in an array of error objects
5. WHEN the Inventory_System encounters an unhandled exception during request processing, THE Inventory_System SHALL return a 500 status code with an error response containing an "error_type" field with value "internal_error" and a "message" field with the value "An internal error occurred"
6. WHEN the Inventory_System receives a request that does not complete within 30 seconds, THE Inventory_System SHALL return a 504 status code with an error response containing an "error_type" field with value "timeout" and a "message" field indicating timeout
7. WHEN the Inventory_System receives a request with an unsupported HTTP method, THE Inventory_System SHALL return a 405 status code with an error response containing an "error_type" field with value "method_not_allowed"
8. THE Inventory_System SHALL log all errors with timestamp, request path, request method, and error details for debugging purposes

### Requirement 10: Persistencia en Memoria

**User Story:** Como desarrollador del sistema, quiero almacenar datos en memoria durante la fase inicial, para simplificar el desarrollo antes de migrar a DynamoDB.

#### Acceptance Criteria

1. THE Inventory_System SHALL store all Products in an in-memory data structure during execution with a maximum capacity of 10000 Products
2. WHEN the Inventory_System starts, THE In_Memory_Store SHALL initialize containing zero Products
3. WHEN an API_Client attempts to create a Product and the In_Memory_Store contains 10000 Products, THE Inventory_System SHALL reject the request, prevent the product from being added to storage, and return a 507 status code with an error message indicating storage capacity exceeded
4. WHEN the Inventory_System stops, THE In_Memory_Store SHALL lose all stored data
5. WHEN the Inventory_System restarts after stopping, THE In_Memory_Store SHALL initialize containing zero Products
