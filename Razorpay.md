### Fetch All Payment Links

Source: https://razorpay.com/docs/api/payments/payment-links/fetch-all-standard

This example demonstrates how to retrieve all payment links using a GET request to the /v1/payment_links/ endpoint.

```APIDOC
## GET /v1/payment_links/

### Description
Fetches a list of all payment links created for your account.

### Method
GET

### Endpoint
https://api.razorpay.com/v1/payment_links/

### Parameters
#### Query Parameters
- **count** (integer) - Optional - The number of payment links to retrieve per page. Default is 10.
- **skip** (integer) - Optional - The number of payment links to skip before starting to collect the result set. Default is 0.

### Request Example
```bash
curl -u [YOUR_KEY_ID]:[YOUR_KEY_SECRET] \
-X GET https://api.razorpay.com/v1/payment_links/ \
-H "content-type: application/json"
```

### Response
#### Success Response (200)
- **payment_links** (array) - A list of payment link objects.
  - **id** (string) - The unique identifier for the payment link.
  - **entity** (string) - The type of entity, typically "payment_link".
  - **amount** (integer) - The amount for which the payment link was created.
  - **currency** (string) - The currency of the amount.
  - **status** (string) - The current status of the payment link (e.g., "paid", "pending", "expired").
  - **description** (string) - A description for the payment link.
  - **customer** (object) - Details of the customer associated with the payment link.
  - **order_id** (string) - The ID of the order associated with the payment link.
  - **created_at** (integer) - Timestamp when the payment link was created.
  - **updated_at** (integer) - Timestamp when the payment link was last updated.
  - **short_url** (string) - A short URL to share the payment link.
  - **long_url** (string) - The full URL for the payment link.
  - **note** (array) - Any notes associated with the payment link.
  - **callback_url** (string) - The URL to redirect to after payment completion.
  - **callback_method** (string) - The HTTP method for the callback URL.

#### Response Example
```json
{
  "payment_links": [
    {
      "accept_partial": true,
      "amount": 10000,
      "amount_paid": 10000,
      "cancelled_at": 0,
      "created_at": 1661852539,
      "currency": "USD",
      "customer": [],
      "description": "Grocery",
      "expire_by": 0,
      "expired_at": 0,
      "first_min_partial_amount": 100,
      "id": "plink_KBnb7I424Rc1R9",
      "notes": [],
      "notify": {
        "email": false,
        "sms": false
      },
      "order_id": "order_KBneAVhT2zbzsU",
      "payments": [],
      "reference_id": "111",
      "reminder_enable": false,
      "reminders": [],
      "short_url": "https://rzp.io/i/alaBxs0i",
      "status": "paid",
      "updated_at": 1661852741,
      "upi_link": false,
      "user_id": "HD1JAKCCPGDfRx"
    }
  ]
}
```

###### Errors
Error Status: 4xx
The api {key/secret} provided is invalid
There is a mismatch between the API credentials passed in the API call and the API credentials generated on the Dashboard.
Solution
```

--------------------------------

### Quick Install Razorpay CLI (macOS/Linux)

Source: https://razorpay.com/docs/api/install-cli

Use this script to automatically detect your OS and architecture, download the latest Razorpay CLI binary, and install it to ~/.local/bin.

```bash
curl -fsSL https://razorpay.com/cli/latest/install.sh | bash
```

--------------------------------

### Verify Razorpay CLI Installation

Source: https://razorpay.com/docs/api/install-cli

Verify that the Razorpay CLI has been installed correctly by checking its version.

```bash
razorpay --version
```

--------------------------------

### Create Payment Link with Custom Options

Source: https://razorpay.com/docs/api/payments/payment-links/customise-options-config

This example demonstrates how to create a payment link and customize the checkout display options, including specifying which payment methods to show and their order.

```APIDOC
## POST /v1/payment_links

### Description
Use this API endpoint for Reordered Payment Methods.

### Method
POST

### Endpoint
https://api.razorpay.com/v1/payment_links/

### Parameters
#### Request Body
- **amount** (integer) - Required - The amount to be charged.
- **currency** (string) - Required - The currency of the amount.
- **accept_partial** (boolean) - Optional - Whether to accept partial payments.
- **first_min_partial_amount** (integer) - Optional - The minimum amount for the first partial payment.
- **reference_id** (string) - Required - Your internal reference ID for the payment.
- **description** (string) - Optional - A description for the payment.
- **customer** (object) - Optional - Customer details.
  - **name** (string) - Optional - Customer name.
  - **contact** (string) - Required - Customer contact number.
  - **email** (string) - Optional - Customer email.
- **notify** (object) - Optional - Notification preferences.
  - **sms** (boolean) - Optional - Enable SMS notifications.
  - **email** (boolean) - Optional - Enable email notifications.
- **reminder_enable** (boolean) - Optional - Enable reminders for the payment.
- **options** (object) - Optional - Customization options for the checkout.
  - **checkout** (object) - Optional - Checkout display configuration.
    - **config** (object) - Optional - Configuration for the checkout display.
      - **display** (object) - Optional - Display settings.
        - **blocks** (object) - Optional - Defines payment method blocks.
          - **banks** (object) - Optional - Configuration for bank payment methods.
            - **name** (string) - Optional - Name of the block.
            - **instruments** (array) - Optional - List of instruments to display.
              - **method** (string) - Required - The payment method (e.g., "card").
        - **sequence** (array) - Optional - The order in which blocks should appear.
        - **preferences** (object) - Optional - User preferences for display.
          - **show_default_blocks** (boolean) - Optional - Whether to show default blocks.

### Request Example
```json
{
  "amount": 1000,
  "currency": "USD",
  "accept_partial": true,
  "first_min_partial_amount": 100,
  "reference_id": "#21132",
  "description": "Payment for policy no #23456",
  "customer": {
    "name": "John Smith",
    "contact": "+11234567890",
    "email": "john.smith@example.com"
  },
  "notify": {
    "sms": true,
    "email": true
  },
  "reminder_enable": true,
  "options": {
    "checkout": {
      "config": {
        "display": {
          "blocks": {
            "banks": {
              "name": "All Payment Methods",
              "instruments": [
                {
                  "method": "card"
                }
              ]
            }
          },
          "sequence": [
            "block.banks"
          ],
          "preferences": {
            "show_default_blocks": false
          }
        }
      }
    }
  }
}
```

### Response
#### Success Response (200)
- **id** (string) - The unique ID of the created payment link.
- **entity** (string) - The type of entity created (e.g., "payment_link").
- **amount** (integer) - The amount of the payment link.
- **currency** (string) - The currency of the payment link.
- **status** (string) - The current status of the payment link (e.g., "created").
- **description** (string) - The description of the payment link.
- **reference_id** (string) - The reference ID provided.
- **customer** (object) - Details of the customer.
- **notify** (object) - Notification settings.
- **reminder_enable** (boolean) - Indicates if reminders are enabled.
- **created_at** (integer) - Timestamp when the payment link was created.
- **short_url** (string) - A short URL to the payment link.

#### Response Example
```json
{
  "accept_partial": true,
  "amount": 1000,
  "amount_paid": 0,
  "callback_method": "",
  "callback_url": "",
  "cancelled_at": 0,
  "created_at": 1596188911,
  "currency": "USD",
  "customer": {
    "contact": "+11234567890",
    "email": "john.smith@example.com",
    "name": "John Smith"
  },
  "deleted_at": 0,
  "description": "Payment for policy no #23456",
  "expire_by": 0,
  "expired_at": 0,
  "first_min_partial_amount": 100,
  "id": "plink_FL3i7DFZwKOaCu",
  "notes": null,
  "notify": {
    "email": true,
    "sms": true
  },
  "payments": null,
  "reference_id": "#21132",
  "reminder_enable": true,
  "reminders": [],
  "short_url": "https://rzp.io/i/l3IB1Sc",
  "source": "",
  "source_id": "",
  "status": "created",
  "updated_at": 1596188911,
  "user_id": ""
}
```
```

--------------------------------

### Payment Downtime Response Example

Source: https://razorpay.com/docs/api/payments/downtime/fetch-all

This is an example of the JSON response when fetching payment downtimes. It shows a single downtime event for the 'card' payment method, indicating it has started and is of high severity.

```json
{
  "payment_downtime": {
    "entity": "collection",
    "count": 1,
    "items": [
      {
        "id": "down_F7LroRQAAFuswd",
        "entity": "payment.downtime",
        "method": "card",
        "begin": 1593196031,
        "end": null,
        "status": "started",
        "scheduled": false,
        "severity": "high",
        "instrument": {
          "network": "VISA"
        },
        "created_at": 1593196089,
        "updated_at": 1593196089
      }
    ]
  }
}

```

--------------------------------

### Payment Link Creation with Custom Payment Methods

Source: https://razorpay.com/docs/api/payments/payment-links/customise-payment-methods

This example demonstrates how to create a Payment Link with various customization options, including partial payments, expiration, notifications, and specific payment method configurations.

```APIDOC
## POST /v1/payment_links

### Description
Create a Payment Link with customizable payment methods and options.

### Method
POST

### Endpoint
/v1/payment_links

### Parameters
#### Request Body
- **amount** (integer) - Required - Amount to be paid using the Payment Link. Must be in the smallest unit of the currency.
- **currency** (string) - Optional - A three-letter ISO code for the currency.
- **accept_partial** (boolean) - Optional - Indicates whether customers can make partial payments. `true` to allow, `false` (default) to disallow.
- **first_min_partial_amount** (integer) - Optional - Minimum amount for the first partial payment. Must be passed along with `accept_partial`.
- **description** (string) - Optional - A brief description of the Payment Link. Max 2048 characters.
- **reference_id** (string) - Optional - Reference number for the Payment Link. Must be unique. Max 40 characters.
- **customer** (json object) - Optional - Customer details.
- **expire_by** (integer) - Optional - Timestamp (Unix) when the Payment Link will expire. Cannot exceed six months from creation.
- **notify** (array) - Optional - Defines who handles Payment Link notifications.
- **notes** (json object) - Optional - Key-value pairs for additional information. Max 15 pairs, 256 characters each.
- **callback_url** (string) - Optional - Redirect URL after payment completion.
- **callback_method** (string) - Optional - Method for the callback URL. Must be `get` if `callback_url` is provided.
- **reminder_enable** (boolean) - Optional - `true` to send reminders, `false` to disable.
- **options** (array) - Optional - Options to display or hide payment methods on the Checkout section.
  - **checkout** (json object) - Optional - Configuration for checkout options.
    - **method** (string) - Optional - Specifies the payment method to be displayed or hidden. Example: `"card"`.
```

--------------------------------

### Start Payment with JSONObject Options

Source: https://razorpay.com/docs/payments/payment-gateway/android-integration/standard/integration-steps

Instantiate the Checkout class and pass payment details and options as a JSONObject. Ensure the order_id from Step 3 is included. This method launches the Razorpay Checkout form.

```Java
public void startPayment() {
  checkout.setKeyID("<YOUR_KEY_ID>");
  /**
   * Instantiate Checkout
   */
  Checkout checkout = new Checkout();


  /**
   * Set your logo here
   */
  checkout.setImage(R.drawable.logo);


  /**
   * Reference to current activity
   */
  final Activity activity = this;


  /**
   * Pass your payment options to the Razorpay Checkout as a JSONObject
   */
  try {
      JSONObject options = new JSONObject();


      options.put("name", "Merchant Name");
      options.put("description", "Reference No. #123456");
      options.put("image", "http://example.com/image/rzp.jpg");
      options.put("order_id", "order_DBJOWzybf0sJbb");//from response of step 3.
      options.put("theme.color", "#3399cc");
      options.put("currency", "USD");
      options.put("amount", "50000");//pass amount in currency subunits
      options.put("prefill.email", "john.smith@example.com");
      options.put("prefill.contact","+11234567890");
      JSONObject retryObj = new JSONObject();
      retryObj.put("enabled", true);
      retryObj.put("max_count", 4);
      options.put("retry", retryObj);


      checkout.open(activity, options);


  } catch(Exception e) {
    Log.e(TAG, "Error in starting Razorpay Checkout", e);
  }
}
```

--------------------------------

### Customise Payment Methods (Example 2)

Source: https://razorpay.com/docs/api/payments/payment-links

Customizes available payment methods using Options and Config Parameters.

```APIDOC
## Customise Payment Methods (Example 2)

### Description
Customises Payment Methods with the Options and Config Parameters.

### Method
POST

### Endpoint
/v1/payment_links/config/payment_methods
```

--------------------------------

### Customise Payment Methods (Example 1)

Source: https://razorpay.com/docs/api/payments/payment-links

Customizes available payment methods using Options and Method Parameters.

```APIDOC
## Customise Payment Methods (Example 1)

### Description
Customises Payment Methods with the Options and Method Parameters.

### Method
POST

### Endpoint
/v1/payment_links/config/payment_methods
```

--------------------------------

### Fetch Orders with Expanded Card Payments

Source: https://razorpay.com/docs/api/orders/fetch-all-expanded-card-payments

This example demonstrates how to make a GET request to the Razorpay API to retrieve orders and expand the associated payments, specifically including card details.

```APIDOC
## GET /v1/orders?expand[]=payments.card

### Description
Fetches a collection of orders, with the option to expand the associated payments to include detailed card information.

### Method
GET

### Endpoint
https://api.razorpay.com/v1/orders?expand[]=payments.card

### Parameters
#### Query Parameters
- **expand[]** (string) - Optional - Specifies which related resources to expand. Use `payments.card` to include card details in the payment information.

### Request Example
```bash
curl -u [YOUR_KEY_ID]:[YOUR_KEY_SECRET] \
-X GET https://api.razorpay.com/v1/orders?expand[]=payments.card
```

### Response
#### Success Response (200)
Returns a collection of order objects, where each order may contain expanded payment details including card information.

- **entity** (string) - The type of the returned object, expected to be "collection".
- **count** (integer) - The number of items in the collection.
- **items** (array) - An array of order objects.
  - **id** (string) - The unique identifier for the order.
  - **entity** (string) - The type of the object, expected to be "order".
  - **amount** (integer) - The total amount of the order.
  - **amount_paid** (integer) - The amount that has been paid for the order.
  - **amount_due** (integer) - The amount that is still due for the order.
  - **currency** (string) - The currency of the order amount.
  - **receipt** (string) - The receipt ID associated with the order.
  - **payments** (object) - Information about the payments made for the order.
    - **entity** (string) - The type of the returned object, expected to be "collection".
    - **count** (integer) - The number of payments.
    - **items** (array) - An array of payment objects.
      - **id** (string) - The unique identifier for the payment.
      - **entity** (string) - The type of the object, expected to be "payment".
      - **amount** (integer) - The amount of the payment.
      - **currency** (string) - The currency of the payment amount.
      - **status** (string) - The status of the payment (e.g., "captured").
      - **order_id** (string) - The ID of the order this payment belongs to.
      - **method** (string) - The payment method used (e.g., "card").
      - **captured** (boolean) - Indicates if the payment has been captured.
      - **card** (object) - Details of the card used for the payment.
        - **id** (string) - The unique identifier for the card.
        - **entity** (string) - The type of the object, expected to be "card".
        - **last4** (string) - The last 4 digits of the card number.
        - **network** (string) - The card network (e.g., "Visa").
        - **type** (string) - The type of the card (e.g., "debit").
      - **created_at** (integer) - The timestamp when the payment was created.
  - **created_at** (integer) - The timestamp when the order was created.

#### Response Example
```json
{
  "entity": "collection",
  "count": 1,
  "items": [
    {
      "id": "order_MjehF7I6RXSm2o",
      "entity": "order",
      "amount": 500,
      "amount_paid": 500,
      "amount_due": 0,
      "currency": "USD",
      "receipt": null,
      "payments": {
        "entity": "collection",
        "count": 1,
        "items": [
          {
            "id": "pay_MjehkbJc3pPERF",
            "entity": "payment",
            "amount": 500,
            "currency": "USD",
            "status": "captured",
            "order_id": "order_MjehF7I6RXSm2o",
            "method": "card",
            "captured": true,
            "card": {
              "id": "card_MjehkeMkNIzhOb",
              "entity": "card",
              "last4": "0153",
              "network": "Visa",
              "type": "debit"
            },
            "created_at": 1696318958
          }
        ]
      },
      "created_at": 1696318929
    }
  ]
}
```

###### Errors
Error Status: 4xx
The API {key/secret} provided is invalid.
The API credentials passed in the API call differ from the ones generated on the Dashboard.
Solution
Change the API key and secret to the correct ones.
```

--------------------------------

### Create Payment Link with Customised Options

Source: https://razorpay.com/docs/api/payments/payment-links/customise-options-config

Use this API endpoint to create a payment link with custom display options for payment methods. This example configures the 'banks' block to show all payment methods and specifies a sequence preference.

```curl
curl
-u [YOUR_KEY_ID]:[YOUR_KEY_SECRET] \
-X POST https://api.razorpay.com/v1/payment_links/ \
-H 'Content-type: application/json' \
-d '{
  "amount": 1000,
  "currency": "USD",
  "accept_partial": true,
  "first_min_partial_amount": 100,
  "reference_id": "#21132",
  "description": "Payment for policy no #23456",
  "customer": {
    "name": "John Smith",
    "contact": "+11234567890",
    "email": "john.smith@example.com"
  },
  "notify": {
    "sms": true,
    "email": true
  },
  "reminder_enable": true,
  "options": {
    "checkout": {
      "config": {
        "display": {
          "blocks": {
            "banks": {
              "name": "All Payment Methods",
              "instruments": [
                {
                  "method": "card"
                },
              ]
            }
          },
          "sequence": [
            "block.banks"
          ],
          "preferences": {
            "show_default_blocks": false
          }
        }
      }
    }
  }
}'
```

--------------------------------

### Successful Order Fetch Response

Source: https://razorpay.com/docs/api/orders/fetch-with-id

This is an example of a successful response when fetching order details. It includes all relevant information about the order, such as its ID, amount, currency, status, and creation timestamp.

```json
{
    "id": "order_DaaS6LOUAASb7Y",
    "entity": "order",
    "amount": 2000,
    "amount_paid": 0,
    "amount_due": 2000,
    "currency": "USD",
    "receipt": null,
    "offer_id": "offer_JGQvQtvJmVDRIA",
    "offers": [
        "offer_JGQvQtvJmVDRIA"
    ],
    "status": "created",
    "attempts": 0,
    "notes": [],
    "created_at": 1654776878
}
```

--------------------------------

### Example Success Response for Fetching Payments

Source: https://razorpay.com/docs/api/orders/fetch-payments

This JSON object represents a successful response when fetching payments for an order. It lists payment details including ID, status, amount, currency, and creation timestamp for each payment.

```json
{
  "entity":"collection",
  "count":2,
  "items":[
    {
      "id":"pay_N8FUmetkCE2hZP",
      "entity":"payment",
      "amount":100,
      "currency":"USD",
      "status":"failed",
      "order_id":"order_N8FRN5zTm5S3wx",
      "invoice_id":null,
      "international":false,
      "method":"ach",
      "amount_refunded":0,
      "refund_status":null,
      "captured":false,
      "description":null,
      "card_id":null,
      "bank":"HSBC",
      "wallet":null,
      "email":"john.smith@example.com",
      "contact":"+11234567890",
      "notes":{
        "notes_key_1":"Tea, Earl Grey, Hot",
        "notes_key_2":"Tea, Earl Grey… decaf."
      },
      "fee":null,
      "tax":null,
      "error_code":"BAD_REQUEST_ERROR",
      "error_description":"Payment was unsuccessful due to a temporary issue. If amount got deducted, it will be refunded within 5-7 working days.",
      "error_source":"gateway",
      "error_step":"payment_response",
      "error_reason":"payment_failed",
      "acquirer_data":{
        "auth_code":null
      },
      "created_at":1701688684
    },
    {
      "id":"pay_N8FVRD1DzYzBh1",
      "entity":"payment",
      "amount":100,
      "currency":"USD",
      "status":"captured",
      "order_id":"order_N8FRN5zTm5S3wx",
      "invoice_id":null,
      "international":false,
      "method":"ach",
      "amount_refunded":0,
      "refund_status":null,
      "captured":true,
      "description":null,
      "card_id":null,
      "bank":"HSBC",
      "wallet":null,
      "email":"john.smith@example.com",
      "contact":"+11234567890",
      "notes":{
        "notes_key_1":"Tea, Earl Grey, Hot",
        "notes_key_2":"Tea, Earl Grey… decaf."
      },
      "fee":2,
      "tax":0,
      "error_code":null,
      "error_description":null,
      "error_source":null,
      "error_step":null,
      "error_reason":null,
      "acquirer_data":{
        "auth_code":null
      },
      "created_at":1701688721
    }
  ]
}
```

--------------------------------

### Fetch a Payment with ID using cURL

Source: https://razorpay.com/docs/api/payments/fetch-with-id

Use this cURL command to make a GET request to retrieve a specific payment by its ID. Replace `[YOUR_KEY_ID]` and `[YOUR_KEY_SECRET]` with your actual API keys.

```curl
curl -u [YOUR_KEY_ID]:[YOUR_KEY_SECRET]
-X GET https://api.razorpay.com/v1/payments/pay_DG4ZdRK8ZnXC3k
```

--------------------------------

### Fetch All Expanded Payments

Source: https://razorpay.com/docs/api/orders/fetch-all-expanded-payments

This endpoint retrieves a list of all payments with their expanded details. It's useful for getting a comprehensive view of all payment transactions.

```APIDOC
## GET /v1/payments

### Description
Retrieves a list of all payments with expanded details.

### Endpoint
/v1/payments

### Response
#### Success Response (200)
- **entity** (string) - The type of entity (e.g., 'payment').
- **count** (integer) - The total number of payments.
- **items** (array) - An array of payment objects.
  - **id** (string) - The unique identifier for the payment.
  - **entity** (string) - The entity type ('payment').
  - **amount** (integer) - The payment amount in the smallest currency unit.
  - **currency** (string) - The currency code (e.g., 'INR').
  - **order_id** (string) - The ID of the associated order.
  - **invoice_id** (string) - The ID of the associated invoice.
  - **international** (boolean) - Indicates if the payment is international.
  - **method** (string) - The payment method used (e.g., 'card', 'netbanking').
  - **amount_refunded** (integer) - The amount that has been refunded.
  - **refund_status** (string) - The status of the refund ('none', 'partial', 'full').
  - **capture_method** (string) - The capture method ('automatic' or 'manual').
  - **description** (string) - A description of the payment.
  - **email** (string) - The email address of the customer.
  - **contact** (string) - The contact number of the customer.
  - **fee** (integer) - The transaction fee.
  - **tax** (integer) - The transaction tax.
  - **status** (string) - The current status of the payment ('created', 'authorized', 'captured', 'failed', 'refunded').
  - **order_id** (string) - The ID of the associated order.
  - **created_at** (integer) - The timestamp when the payment was created.
  - **bank_account** (object) - Details of the bank account used for the payment.
    - **card_network** (string) - The network of the card.
    - **card_type** (string) - The type of the card.
    - **bank_name** (string) - The name of the bank.
  - **error_details** (object) - Details about any errors encountered during the payment.
    - **error_code** (string) - The error code.
    - **error_description** (string) - A description of the error.
    - **error_source** (string) - The source of the error.
    - **error_step** (string) - The step where the error occurred.
    - **error_reason** (string) - The reason for the error.
    - **created_at** (integer) - The timestamp when the error occurred.

#### Response Example
{
  "entity": "payment",
  "count": 1,
  "items": [
    {
      "id": "pay_Ff4j7f8f8f8f8f",
      "entity": "payment",
      "amount": 50000,
      "currency": "INR",
      "order_id": "order_Ff4j7f8f8f8f8f",
      "invoice_id": null,
      "international": false,
      "method": "card",
      "amount_refunded": 0,
      "refund_status": null,
      "capture_method": "automatic",
      "description": "Test payment",
      "email": "test@example.com",
      "contact": "+919999999999",
      "fee": 1500,
      "tax": 270,
      "status": "captured",
      "order_id": "order_Ff4j7f8f8f8f8f",
      "created_at": 1589160718,
      "bank_account": {
        "card_network": "Visa",
        "card_type": "debit",
        "bank_name": "Test Bank"
      },
      "error_details": {
        "error_code": null,
        "error_description": null,
        "error_source": null,
        "error_step": null,
        "error_reason": null,
        "created_at": 1589269450
      }
    }
  ]
}
```

--------------------------------

### Create Payment Link

Source: https://razorpay.com/docs/api/payments/payment-links/change-business-name

This section details how to create a payment link using the Razorpay API. It includes the HTTP method, endpoint, request body parameters, and an example request.

```APIDOC
## POST /v1/payment_links

### Description
Creates a new payment link that can be shared with customers for making payments.

### Method
POST

### Endpoint
https://api.razorpay.com/v1/payment_links/

### Parameters
#### Request Body
- **amount** (integer) - Required - The amount to be charged in the smallest currency unit (e.g., 1000 for $10.00).
- **currency** (string) - Required - The currency of the payment (e.g., USD, INR).
- **accept_partial** (boolean) - Optional - Allows partial payments. Defaults to false.
- **first_min_partial_amount** (integer) - Optional - The minimum amount for the first partial payment if `accept_partial` is true.
- **reference_id** (string) - Required - A unique identifier for the payment link.
- **description** (string) - Optional - A description for the payment link.
- **customer** (object) - Optional - Customer details.
  - **name** (string) - Required if customer object is present - Customer's name.
  - **contact** (string) - Required if customer object is present - Customer's contact number.
  - **email** (string) - Required if customer object is present - Customer's email address.
- **notify** (object) - Optional - Notification preferences.
  - **sms** (boolean) - Optional - Enable SMS notifications.
  - **email** (boolean) - Optional - Enable email notifications.
- **reminder_enable** (boolean) - Optional - Enable reminders for the payment link. Defaults to false.
- **options** (object) - Optional - Additional options.
  - **checkout** (object) - Optional - Checkout specific options.
    - **name** (string) - Optional - The name displayed on the checkout page.

### Request Example
```json
{
  "amount": 1000,
  "currency": "USD",
  "accept_partial": true,
  "first_min_partial_amount": 100,
  "reference_id": "#2234542",
  "description": "Payment for policy no #23456",
  "customer": {
    "name": "John Smith",
    "contact": "+11234567890",
    "email": "john.smith@example.com"
  },
  "notify": {
    "sms": true,
    "email": true
  },
  "reminder_enable": true,
  "options": {
    "checkout": {
      "name": "Lacme Corp"
    }
  }
}
```

### Response
#### Success Response (200)
- **id** (string) - Unique identifier for the created payment link.
- **entity** (string) - Type of entity, usually 'payment_link'.
- **amount** (integer) - The amount charged.
- **currency** (string) - The currency of the payment.
- **accept_partial** (boolean) - Indicates if partial payments are accepted.
- **first_min_partial_amount** (integer) - Minimum amount for the first partial payment.
- **reference_id** (string) - The reference ID provided.
- **description** (string) - The description of the payment link.
- **status** (string) - The current status of the payment link (e.g., 'created').
- **created_at** (integer) - Timestamp when the payment link was created.
- **customer** (object) - Details of the customer.
- **notify** (object) - Notification settings.
- **reminder_enable** (boolean) - Indicates if reminders are enabled.
- **short_url** (string) - A short URL to the payment link.

#### Response Example
```json
{
  "accept_partial": true,
  "amount": 1000,
  "amount_paid": 0,
  "callback_method": "",
  "callback_url": "",
  "cancelled_at": 0,
  "created_at": 1596187657,
  "currency": "USD",
  "customer": {
    "contact": "+11234567890",
    "email": "john.smith@example.com",
    "name": "John Smith"
  },
  "description": "Payment for policy no #23456",
  "expire_by": 0,
  "expired_at": 0,
  "first_min_partial_amount": 100,
  "id": "plink_FL3M2gJFs1Jkma",
  "notes": null,
  "notify": {
    "email": true,
    "sms": true
  },
  "payments": null,
  "reference_id": "#2234542",
  "reminder_enable": true,
  "reminders": [],
  "short_url": "https://rzp.io/i/at2OOsR",
  "source": "",
  "source_id": "",
  "status": "created",
  "updated_at": 1596187657,
  "user_id": ""
}
```
```

--------------------------------

### API Response with Expanded Payments

Source: https://razorpay.com/docs/api/orders/fetch-all-expanded-payments

This is an example of a successful API response when requesting orders with expanded payment details. The 'items' array contains order objects, each with a nested 'payments' object detailing associated transactions.

```json
{
  "entity": "collection",
  "count": 2,
  "items": [
    {
      "id": "order_EpMTIJM0rhOj3H",
      "entity": "order",
      "amount": 10000,
      "amount_paid": 0,
      "amount_due": 10000,
      "currency": "USD",
      "receipt": null,
      "payments": {
        "entity": "collection",
        "count": 1,
        "items": [
          {
            "id": "pay_EpMq4YcK0z5UYk",
            "entity": "payment",
            "amount": 10000,
            "currency": "USD",
            "status": "authorized",
            "order_id": "order_EpMTIJM0rhOj3H",
            "invoice_id": null,
            "international": false,
            "method": "card",
            "amount_refunded": 0,
            "refund_status": null,
            "captured": false,
            "description": null,
            "card_id": "card_EpMq4e7H6fHBQZ",
            "bank": null,
            "wallet": null,
            "vpa": null,
            "email": "john.smith@example.com",
            "contact": "+11234567890",
            "notes": [],
            "fee": null,
            "tax": null,
            "error_code": null,
            "error_description": null,
            "error_source": null,
            "error_step": null,
            "error_reason": null,
            "created_at": 1589269390
          }
        ]
      },
      "offer_id": null,
      "status": "attempted",
      "attempts": 1,
      "notes": [],
      "created_at": 1589268096
    },
    {
      "id": "order_Eoryq8z9wd0y7i",
      "entity": "order",
      "amount": 10000,
      "amount_paid": 0,
      "amount_due": 10000,
      "currency": "USD",
      "receipt": null,
      "payments": {
        "entity": "collection",
        "count": 1,
        "items": [
          {
            "id": "pay_EpMr7r6DRIdYPO",
            "entity": "payment",
            "amount": 10000,
            "currency": "USD",
            "status": "authorized",
            "order_id": "order_Eoryq8z9wd0y7i",
            "invoice_id": null,
            "international": false,
            "method": "card",
            "amount_refunded": 0,
            "refund_status": null,
            "captured": false,
            "description": null,
            "card_id": "card_EpMr7y6E5cDXvd",
            "bank": null,
            "wallet": null,
            "vpa": null,
            "email": "john.smith@example.com",
            "contact": "+11234567890",
            "notes": [],
            "fee": null,
            "tax": null
          }
        ]
      }
    }
  ]
}
```

--------------------------------

### Fetch Payment Downtime Details With ID

Source: https://razorpay.com/docs/api/payments/downtime

Retrieves the specific details of a single payment downtime using its unique identifier. This is useful for getting granular information about a particular downtime event.

```APIDOC
## Fetch Payment Downtime Details With ID

### Description
Retrieves details of a Payment Downtime with id.

### Method
GET

### Endpoint
/v1/payments/downtime/{id}
```

--------------------------------

### Fetch Payment Downtime Details With ID using cURL

Source: https://razorpay.com/docs/api/payments/downtime/fetch-with-id

Use this cURL command to make a GET request to fetch the details of a specific payment downtime by its ID. Ensure you replace placeholder values with your actual API key, secret, and the downtime ID.

```curl
curl -u <YOUR_KEY_ID>:<YOUR_KEY_SECRET> \
-X GET https://api.razorpay.com/v1/payments/downtimes/down_F1cxDoHWD4fkQt \
-H "Content-Type: application/json" \

```

--------------------------------

### Fetch Downtime by ID using cURL

Source: https://razorpay.com/docs/api/payments/downtime/fetch-with-id

Use this cURL command to make a GET request to the Razorpay API to retrieve downtime details for a specific ID. Replace `<YOUR_KEY_ID>` and `<YOUR_KEY_SECRET>` with your actual API credentials.

```bash
curl -u <YOUR_KEY_ID>:<YOUR_KEY_SECRET> \
-X GET https://api.razorpay.com/v1/payments/downtimes/down_F1cxDoHWD4fkQt \
-H "Content-Type: application/json" \
```

--------------------------------

### Update Order Notes using cURL

Source: https://razorpay.com/docs/api/orders/update

Use this cURL command to update the 'Notes' field of an existing order. Ensure you replace placeholder values with your actual key ID, key secret, and order ID. This example demonstrates adding or modifying key-value pairs within the notes.

```curl
curl -u [YOUR_KEY_ID]:[YOUR_KEY_SECRET]\
-X PATCH https://api.razorpay.com/v1/orders/order_DaaS6LOUAASb7Y \
-d '{
  "notes": {
    "key1": "value3",
    "key2": "value2"
  }
}'
```

--------------------------------

### Payment Downtime Entity Structure

Source: https://razorpay.com/docs/api/payments/downtime/entity

The Payment Downtime Entity represents a downtime event for a specific payment method. It includes details such as the downtime ID, payment method, start and end times, status, severity, and instrument details.

```APIDOC
## Payment Downtime Entity

### Description
Represents a downtime event for a specific payment method, including its status, severity, and timing.

### Parameters

#### `id` (string) - Required
Unique identifier of the downtime's occurrence.

#### `entity` (string) - Required
Type of the entity, which is `payment.downtime`.

#### `method` (string) - Required
The payment method experiencing downtime. Possible values: `card`, `ach`.

#### `begin` (integer) - Required
Timestamp (in Unix) indicating the start of the downtime.

#### `end` (integer) - Optional
Timestamp (in Unix) indicating the end of the downtime. Set to `null` if the end-time is unknown.

#### `status` (string) - Required
Status of the downtime. Possible statuses: `scheduled`, `started`, `resolved`, `updated`.

#### `scheduled` (boolean) - Required
Indicates if the downtime is scheduled (`true`) or unscheduled (`false`).

#### `severity` (string) - Required
Severity of the downtime. Possible values: `high`, `medium`, `low`.

#### `instrument` (object) - Optional
Details about the instrument affected by the downtime.
  - `issuer` (string) - The issuer of the instrument.
  - `card_type` (string) - The type of card used (e.g., `credit`, `debit`).

#### `created_at` (integer) - Required
Timestamp (in Unix) when the downtime was recorded.

#### `updated_at` (integer) - Required
Timestamp (in Unix) when the downtime record was last updated.

### Response Example
```json
{
  "id": "down_F7LroRQAAFuswd",
  "method": "card",
  "begin": 1593196031,
  "end": null,
  "status": "started",
  "scheduled": false,
  "severity": "high",
  "instrument": {
    "issuer": "HSBC",
    "card_type": "credit"
  },
  "created_at": 1593196089,
  "updated_at": 1593196089
}
```
```

--------------------------------

### Payment Downtime Entity Structure

Source: https://razorpay.com/docs/api/payments/downtime/entity

The Payment Downtime entity represents an occurrence of downtime for a specific payment method. It includes details such as the downtime ID, the affected payment method, timestamps for when the downtime started and ended (if known), its current status, whether it was scheduled, and its severity.

```APIDOC
## Payment Downtime Entity

### Description
Represents an occurrence of downtime for a specific payment method.

### Parameters

- **id** (string) - Unique identifier of the downtime's occurrence.
- **entity** (string) - Always `payment.downtime`.
- **method** (string) - The payment method experiencing downtime. Possible values: `card`, `ach`.
- **begin** (integer) - Timestamp (in Unix) indicating the start of the downtime.
- **end** (integer) - Timestamp (in Unix) indicating the end of the downtime. `null` if unknown.
- **status** (string) - Status of the downtime. Possible values: `scheduled`, `started`, `resolved`, `updated`.
- **scheduled** (boolean) - Indicates if the downtime is scheduled (`true`) or unscheduled (`false`).
- **severity** (string) - Severity of the downtime. Possible values: `high`, `medium`, `low`.
- **instrument** (object) - Details about the payment instrument affected.
  - **issuer** (string) - The issuer of the card.
  - **card_type** (string) - The type of card. Possible values: `credit`, `debit`.
- **created_at** (integer) - Timestamp (in Unix) when the downtime was recorded.
- **updated_at** (integer) - Timestamp (in Unix) when the downtime record was updated.

### Request Example
```json
{
  "id": "down_F7LroRQAAFuswd",
  "method": "card",
  "begin": 1593196031,
  "end": null,
  "status": "started",
  "scheduled": false,
  "severity": "high",
  "instrument": {
    "issuer": "HSBC",
    "card_type": "credit"
  },
  "created_at": 1593196089,
  "updated_at": 1593196089
}
```

### Response Example
(Same as Request Example for entity representation)
```

--------------------------------

### Payment Downtime Entity Structure

Source: https://razorpay.com/docs/api/payments/downtime/entity

This JSON object represents a payment downtime event. It includes details such as the unique ID, payment method affected, start and end times, current status, severity, and instrument-specific information. The 'end' time is null if the downtime is ongoing or unscheduled.

```json
{
  "id": "down_F7LroRQAAFuswd",
  "method": "card",
  "begin": 1593196031,
  "end": null,
  "status": "started",
  "scheduled": false,
  "severity": "high",
  "instrument": {
    "issuer": "HSBC",
    "card_type": "credit"
  },
  "created_at": 1593196089,
  "updated_at": 1593196089
}
```