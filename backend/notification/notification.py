import boto3
import json
import logging
import os
from botocore.exceptions import ClientError
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)
logging.basicConfig(level=logging.INFO)

AWS_REGION = os.environ['AWS_REGION']
AWS_ACCESS_KEY_ID = os.environ['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = os.environ['AWS_SECRET_ACCESS_KEY']
SNS_TOPIC_ARN = os.environ['SNS_TOPIC_ARN']
SNS_CLIENT = boto3.client(
    'sns',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

SQS_CLIENT = boto3.client(
    'sqs',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def jsonResponse(rescode, **kwargs):
    res_data = {key: value for key, value in kwargs.items()}
    return jsonify(res_data), rescode

def create_queue_with_policy(manager_id):
    queue_name = f"{manager_id}_queue"
    
    # Check if queue already exists
    response = SQS_CLIENT.create_queue(QueueName=queue_name)
    queue_url = response['QueueUrl']
    
    # Get the queue ARN (used for subscription to SNS)
    queue_arn = SQS_CLIENT.get_queue_attributes(
        QueueUrl=queue_url,
        AttributeNames=['QueueArn']
    )['Attributes']['QueueArn']

    # Attach a policy to allow SNS to publish messages to this queue
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": "*",
                "Action": "SQS:SendMessage",
                "Resource": queue_arn,
                "Condition": {
                    "ArnEquals": {"aws:SourceArn": SNS_TOPIC_ARN}
                }
            }
        ]
    }

    SQS_CLIENT.set_queue_attributes(
        QueueUrl=queue_url,
        Attributes={
            'Policy': json.dumps(policy)
        }
    )

    return queue_url, queue_arn

def subscribe_queue_to_sns(queue_arn):
    response = SNS_CLIENT.subscribe(
        TopicArn=SNS_TOPIC_ARN,
        Protocol='sqs',
        Endpoint=queue_arn
    )
    subscription_arn = response['SubscriptionArn']
    logging.info(f"Subscribed queue {queue_arn} to SNS topic. SubscriptionArn: {subscription_arn}")
    return subscription_arn

def configure_message_to_manager(data):
    request_id = data['request_id']
    staff_id = data['staff_id']
    requestor = data['full_name']
    request_type = data['request_type']
    reporting_manager_id = data['reporting_manager_id']

    message = {
        'request_id': request_id,
        'reqest_type': request_type,
        'staff_id': staff_id,
        'requestor': requestor,
        'reporting_manager_id': reporting_manager_id,
        'message': f"Received a WFH request from {requestor}"
    }
    return message

def configure_message_to_staff(data):
    request_id = data['request_id'] # req id will reference the wfh request id
    manager_id = data["manager_id"] # This will be the manager id
    staff_id = data['staff_id'] # In this case this will be the staff id
    sender = data['full_name'] # This will be manager name
    request_type = data['request_type']

    msg = f"Your WFH request ID: {request_id} "
    if request_type == "rejection":
        msg += "is rejected"
    elif request_type == "approval":
        msg += "is approved"

    message = {
        'request_id': request_id,
        'manager_id': manager_id,
        'staff_id': staff_id,
        'sender': sender,
        'message': msg
    }
    return message

def publish_message_to_sns(message):
    SNS_CLIENT.publish(
        TopicArn=SNS_TOPIC_ARN,
        Message=json.dumps(message)
    )


@app.route('/notifications/notify/manager', methods=['POST'])
def notify_manager():
    try:
        data = request.json      
        queue_url, queue_arn = create_queue_with_policy(data['reporting_manager_id'])
        subscribe_queue_to_sns(queue_arn)
        message = configure_message_to_manager(data)
        print(message)
        publish_message_to_sns(message)
        
        return jsonResponse(201, message="Notification sent!")
    except KeyError as e:
        return jsonResponse(400, message=f"Missing required field: {str(e)}")
    except Exception as e:
        return jsonResponse(500, message="Internal server error")
    
@app.route('/notifications/notify/staff', methods=['POST'])
def notify_staff():
    try:
        data = request.json      
        if data["request_type"] not in ["rejection", "approval"]:
            raise Exception(f"Wrong request type, can either be rejection or approval, not {data['request_type']}")
        
        queue_url, queue_arn = create_queue_with_policy(data['staff_id'])
        subscribe_queue_to_sns(queue_arn)
        message = configure_message_to_staff(data)
        print(message)
        publish_message_to_sns(message)
        
        return jsonResponse(201, message="Notification sent!")
    except KeyError as e:
        return jsonResponse(400, message=f"Missing required field: {str(e)}")
    except Exception as e:
        return jsonResponse(500, message=f"Error: {e}")

@app.route('/notifications/receive/<string:staff_id>', methods=['GET'])
def get_notifications(staff_id):
    try:
        id = staff_id        
        queue_name = f"{id}_queue"
        
        # Get the queue URL for this manager's queue
        response = SQS_CLIENT.get_queue_url(QueueName=queue_name)
        queue_url = response['QueueUrl']
        
        # Receive messages from the queue
        response = SQS_CLIENT.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10, 
            WaitTimeSeconds=5, 
            VisibilityTimeout=30  
        )
        
        messages = response.get('Messages', [])
        if messages:
            # Process the messages and delete them from the queue
            for message in messages:
                # Delete each message after receiving it
                receipt_handle = message['ReceiptHandle']
                SQS_CLIENT.delete_message(QueueUrl=queue_url, ReceiptHandle=receipt_handle)
            
            return jsonResponse(200, messages=messages)
        else:
            return jsonResponse(200, messages="No messages available")
    except Exception as e:
        return jsonResponse(500, message="Internal server error")

@app.route('/notifications/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'service': 'notification-service'
    }), 200


if __name__ == "__main__":
    print(f"This is flask complex microservice {os.path.basename(__file__)} for the notification service") # pragma: no cover
    app.run(host="0.0.0.0", port=3000, debug=True) # pragma: no cover
