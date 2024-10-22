1.	Student filter and select the study resources he/she wants to purchase on Marketplace UI, go to the cart page, enter their credit card details (Number, Expiration Date, CVC) and click on the âsubmit paymentâ button. UI generates paymentmethodID via Stripe API and invokes Purchase Study Resource(PSR) microservice (MS) and send all information to PSR
2.	PSR complex MS then invokes User MS via HTTP GET to get seller payment credentials (StripeAccountID). 
3.	User MS validates request using its JWT middleware and returns seller payment credentials (StripeAccountID)
4.	PSR MS then invokes Payment MS via HTTP POST and sends userID, sellerID, total price, description of purchase, sellerâs stripeAccountID and paymentMethodID
5.	Payment MS then processes the payment using Stripe API and returns the payment outcome generated from StripeAPI
6.	Successful outcome from Payment MS leads to PSR MS invoking StudyResource MS via HTTP GET to get study resource links
7.	StudyResource MS looks for 1-1 match of sent resourceID(s) to url of resources stored on AWS S3 Bucket (resourceS3URL) and returns the URL(s)
8.	PSR MS then sends a notification message to Notification MS via [RKEY] order.notification, which Notification MS then sends a message to the user's Telegram via a Telegram bot. 
9.	PSR returns resource link(s) back to Marketplace UI which it then routes users to /marketplace/resource-links for students to see the resources they have purchased
10. asjdisajdiasdjasid jaisdja