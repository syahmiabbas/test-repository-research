### User
> 1.	Student filter and select the study resources he/she wants to purchase on Marketplace UI, go to the cart page, enter their credit card details (Number, Expiration Date, CVC) and click on the submit payment button. UI generates paymentmethodID via Stripe API and invokes Purchase Study Resource(PSR) microservice (MS) and send all information to PSR
2.	PSR complex MS then invokes User MS via HTTP GET to get seller payment credentials (StripeAccountID). 
3.	User MS validates the request using its JWT middleware and retrieves the seller's payment credentials, specifically the Stripe Account ID
4.	PSR MS then invokes Payment MS via HTTP POST and sends userID, sellerID, total price, description of purchase, sellers stripeAccountID and paymentMethodID
5.	Payment MS then processes the payment using Stripe API and returns the payment outcome generated from StripeAPI
6.	Successful outcome from Payment MS leads to PSR MS invoking StudyResource MS via HTTP GET to get study resource links
7.	StudyResource MS looks for 1-1 match of sent resourceID(s) to url of resources stored on AWS S3 Bucket (resourceS3URL) and returns the URL(s)
8.	PSR MS then sends a notification message to Notification MS via [RKEY] order.notification, which Notification MS then sends a message to the user's Telegram via a Telegram bot. 
9.	PSR returns resource link(s) back to Marketplace UI which it then routes users to /marketplace/resource-links for students to see the resources they have purchased
10. User submits invoice
11. User acknowledgess

---
### GPT
The provided text outlines a sequence of operations in a microservices architecture for a marketplace application. Below is a structured representation of the process in a more readable format, using markdown for clarity.

```markdown
## Marketplace Purchase Flow

1. **Student Interaction**:
   - The student filters and selects study resources on the Marketplace UI.
   - They navigate to the cart page, enter credit card details (Number, Expiration Date, CVC), and click the submit payment button.
   - The UI generates a `paymentMethodID` via the Stripe API and invokes the Purchase Study Resource (PSR) microservice, sending all relevant information.

2. **PSR Microservice**:
   - The PSR microservice invokes the User microservice via HTTP GET to retrieve the seller's payment credentials (StripeAccountID).

3. **User Microservice**:
   - The User microservice validates the request using JWT middleware and retrieves the seller's payment credentials, specifically the Stripe Account ID.

4. **Payment Processing**:
   - The PSR microservice invokes the Payment microservice via HTTP POST, sending the following data:
     - `userID`
     - `sellerID`
     - `total price`
     - `description of purchase`
     - `seller's stripeAccountID`
     - `paymentMethodID`

5. **Payment Microservice**:
   - The Payment microservice processes the payment using the Stripe API and returns the payment outcome generated from the Stripe API.

6. **Resource Retrieval**:
   - A successful payment outcome from the Payment microservice leads the PSR microservice to invoke the StudyResource microservice via HTTP GET to retrieve study resource links.

7. **StudyResource Microservice**:
   - The StudyResource microservice looks for a 1-1 match of the sent `resourceID(s)` to the URLs of resources stored in an AWS S3 Bucket (`resourceS3URL`) and returns the URL(s).

8. **Notification**:
   - The PSR microservice sends a notification message to the Notification microservice via `[RKEY] order.notification`.
   - The Notification microservice then sends a message to the user's Telegram via a Telegram bot.

9. **Response to Marketplace UI**:
   - The PSR microservice returns the resource link(s) back to the Marketplace UI, which routes users to `/marketplace/resource-links` for students to view the resources they have purchased.

10. **Invoice Submission**:
    - The user submits an invoice.

11. **User Acknowledgment**:
    - The user acknowledges the transaction.
```

This structured format helps in understanding the flow of operations and interactions between different microservices in the system. If you need further analysis or specific code snippets related to any part of this process, please let me know!
