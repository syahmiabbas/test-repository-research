import os
import json
import logging 
from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
from invokes import invoke_http
import amqp_connection
import pika
load_dotenv()

app = Flask(__name__)
CORS(app)
logging.basicConfig(level=logging.INFO)

exchangename = os.environ.get('EXCHANGENAME') 
exchangetype = os.environ.get('EXCHANGETYPE') 

try:
    connection = amqp_connection.create_connection() 
    channel = connection.channel()
except Exception as e:
    print(f"Error establishing connection to RabbitMQ: {e}")
    channel = None  # Set channel to None if connection fails

def jsonResponse(rescode, **kwargs):
    res_data = {key: value for key, value in kwargs.items()}
    return jsonify(res_data), rescode

studyresourceURL = "http://studyresource:8000/studyresources"
userURL = "http://user:3000/user/paymentdetails"
paymentURL = "http://payment:8080/payment"
paymentRefundURL = "http://payment:8080/refund"

@app.route("/purchasestudyresource", methods=['POST'])
def purchase_study_resource():
    try:
        # Check if data parsed are in JSON format    
        if request.is_json:
            data = request.get_json()
            result = processResourcePurchase(data['SellerID'], data['Price'], data['Resources'], data['PaymentMethodID'], data['Description'], data['UserID'])    
            return jsonResponse(200, message=f"Study resource ID: {data['Resources']} purchased!", data=result)
        else:
            return jsonResponse(400, message="Invalid JSON input")
    except Exception as e:
        message_tele = {
            "chat_id": "1492516288",             
            "telegram_message": "Dear user, apologies for the inconvenience, but our service is currently experiencing technical difficulties. Please try again later, and we'll work diligently to resolve the issue as soon as possible. Thank you for your patience and understanding.",
        }
        message_json = json.dumps(message_tele)
        logging.error(f'Error purchasing resource: {e}')
        telegram_bot_notification(message_json)
        return jsonResponse(500, message=f"Purchase study resource internal error: {e}")
    
def processResourcePurchase(sellerID:int, price: float, resources: list, paymentMethodID:str, desc:str, buyerID:str) -> None:    
    """
    Process a resource purchase transaction.

    Args:        
        sellerID (int): The ID of the seller.
        price (float): The total purchase cost
        resources (list): Array of the ID of the resources being purchased.
        paymentMethodID (str): To generate Stripe intent
        desc (str): Description of the purchase
        buyerID (int): The ID of the buyer.        
    """
    print(sellerID, price, resources, paymentMethodID, desc, buyerID)

    print("\n --------INVOKING user microservice GET SELLER STRIPE ACC ID--------")
    user_result = invoke_http(userURL, method="GET", json={"UserID": int(sellerID)})    
    sellerStripeAccID = user_result['data']
    print(sellerStripeAccID)
    logging.info(f'Successfully get seller stripe account id: {sellerStripeAccID}')

    print("\n --------INVOKING payment microservice MAKE PURCHASE--------")
    paymentBody = {
        "Price": float(price),
        "Description": str(desc),
        "UserID":  str(buyerID),
        "SellerID": str(sellerID),
        "StripeAccountID": str(sellerStripeAccID),
        "PaymentMethodID": str(paymentMethodID)
    }      
    paymentResult = invoke_http(paymentURL, method="POST", json=paymentBody)
    print(paymentResult)
    paymentIntent = paymentResult["PaymentIntentID"]
    if "code" in paymentResult:
        raise Exception           
    logging.info(f'Payment processing outcome: {paymentResult}')

    print("\n --------INVOKING studyresource microservice GET RESOURCE--------")
    try:
        urlLinks = {}    
        for resource in resources:
            print(resource)
            resource_result = invoke_http(f"{studyresourceURL}/{resource['resourceID']}", method="GET")            
            url = resource_result['data']['resources3URL']
            print(f"resource: {url} obtained")
            urlLinks[resource['resourceName']] = url
        
    except Exception as e:
        logging.info(f'Invoking payment rollback due to resource retrieval error')       
        refund_result = invoke_http(f"{paymentRefundURL}/{paymentIntent}", method="PATCH")
        logging.info(f'Refund operation result: {refund_result}')
        logging.info(f'Successfully refunded user')
        raise Exception

    print("\n --------INVOKING Notification queue--------")    
    if connection is None or channel is None:
        print("AMQP connection not established. Skipping notification.")
        return urlLinks
    try:
        count = len(urlLinks)        
        message_tele = {
            "chat_id": "1492516288",             
            "telegram_message": f"[REF ID]: {paymentMethodID}\n\nHello! Thanks for purchasing {count} study resource(s) with us! Your resources are now available for viewing!",
        }
        message_json = json.dumps(message_tele)
        telegram_bot_notification(message_json)        
    except Exception as e:       
        print(f"Purchase study resource Notification queue invocation error ==> {e}")
    return urlLinks

def telegram_bot_notification(message):
    channel.basic_publish(exchange=exchangename, routing_key="order.notification", body=message, properties=pika.BasicProperties(delivery_mode = 2)) 

if __name__ == "__main__":
    print(f"This is flask complex microservice {os.path.basename(__file__)} for purchasing study resource")          
    app.run(host="0.0.0.0", port=5100, debug=True)
