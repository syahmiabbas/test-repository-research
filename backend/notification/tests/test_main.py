import json
import os
import unittest
from unittest.mock import patch, MagicMock
from botocore.exceptions import ClientError 
from notification import app, configure_message_to_staff

class TestNotificationService(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = app.test_client()
        cls.app.testing = True
    
    def test_health_check(self):
        response = self.app.get('/notifications/health')
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data)['status'], 'healthy')
        self.assertEqual(json.loads(response.data)['service'], 'notification-service')

    @patch('notification.SQS_CLIENT')
    @patch('notification.SNS_CLIENT')
    def test_notify_manager(self, mock_sns_client, mock_sqs_client):
        # Mock the response for the SQS client methods
        mock_sqs_client.create_queue.return_value = {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test'}
        mock_sqs_client.get_queue_attributes.return_value = {
            'Attributes': {'QueueArn': 'arn:aws:sqs:us-east-1:123456789012:test'}
        }
        mock_sns_client.subscribe.return_value = {'SubscriptionArn': 'arn:aws:sns:us-east-1:123456789012:test'}
        mock_sns_client.publish.return_value = {}

        # Define the payload for the POST request
        payload = {
            'request_id': '1234',
            'staff_id': 5678,
            'full_name': 'John Doe',
            'request_type': 'WFH Request',
            'reporting_manager_id': 91011
        }

        # Perform the POST request
        response = self.app.post('/notifications/notify/manager', json=payload)
        
        # Assert the response
        self.assertEqual(response.status_code, 201)
        self.assertEqual(json.loads(response.data)['message'], "Notification sent!")

        # Assert that the mocks were called as expected
        mock_sqs_client.create_queue.assert_called_once_with(QueueName='91011_queue')
        mock_sns_client.subscribe.assert_called_once()
        mock_sns_client.publish.assert_called_once()

    @patch('notification.SQS_CLIENT')
    def test_get_notifications(self, mock_sqs_client):
        # Mock the response for the SQS client methods
        mock_sqs_client.get_queue_url.return_value = {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test'}
        mock_sqs_client.receive_message.return_value = {
            'Messages': [{'Body': json.dumps({'msg': 'Test message'}), 'ReceiptHandle': 'test-receipt-handle'}]
        }

        # Perform the GET request
        response = self.app.get('/notifications/receive/5678')
        
        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertIn('messages', json.loads(response.data))
        self.assertEqual(len(json.loads(response.data)['messages']), 1)

        # Assert that delete_message was called
        mock_sqs_client.delete_message.assert_called_once()

    @patch('notification.SQS_CLIENT')
    def test_get_notifications_no_messages(self, mock_sqs_client):
        # Mock the response for no messages
        mock_sqs_client.get_queue_url.return_value = {'QueueUrl': 'https://sqs.us-east-1.amazonaws.com/123456789012/test'}
        mock_sqs_client.receive_message.return_value = {'Messages': []}

        # Perform the GET request
        response = self.app.get('/notifications/receive/5678')

        # Assert the response
        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data)['messages'], "No messages available")

    @patch('notification.SQS_CLIENT')
    def test_get_notifications_exception(self, mock_sqs_client):
        # Simulate exception in get_notifications method
        staff_id = 12345  # Example staff ID
        mock_sqs_client.get_queue_url.side_effect = Exception("Some error occurred")
        
        response = self.app.get(f'/notifications/receive/{staff_id}')
        self.assertEqual(response.status_code, 500)
        self.assertIn(b"Internal server error", response.data)

    @patch('notification.SQS_CLIENT') 
    @patch('notification.SNS_CLIENT')
    def test_notify_manager_key_error(self, mock_sns_client, mock_sqs_client):
        # Prepare test data without the 'reporting_manager_id' to trigger KeyError
        test_data = {
            'request_id': 1,
            'staff_id': 12345,
            'full_name': 'John Doe',
            'request_type': 'full_day'
        }

        with app.test_client() as client:
            response = client.post('/notifications/notify/manager', 
                                    data=json.dumps(test_data),
                                    content_type='application/json')
            self.assertEqual(response.status_code, 400)
            self.assertIn(b"Missing required field:", response.data)

    @patch('notification.SQS_CLIENT') 
    @patch('notification.SNS_CLIENT')
    def test_notify_manager_generic_exception(self, mock_sns_client, mock_sqs_client):
        # Setup the mock to raise a generic exception
        mock_sqs_client.create_queue.side_effect = Exception("Some error occurred")

        test_data = {
            'reporting_manager_id': 6789,
            'request_id': 1,
            'staff_id': 12345,
            'full_name': 'John Doe',
            'request_type': 'full_day'
        }

        with app.test_client() as client:
            response = client.post('/notifications/notify/manager', 
                                    data=json.dumps(test_data),
                                    content_type='application/json')
            self.assertEqual(response.status_code, 500)
            self.assertIn(b"Internal server error", response.data)

    @patch('notification.SQS_CLIENT')  
    @patch('notification.SNS_CLIENT') 
    def test_notify_staff_success(self, mock_sns_client, mock_sqs_client):
        # Mock the necessary methods
        mock_sqs_client.create_queue.return_value = {'QueueUrl': 'test_queue_url'}
        mock_sqs_client.get_queue_attributes.return_value = {'Attributes': {'QueueArn': 'test_queue_arn'}}
        mock_sns_client.subscribe.return_value = {'SubscriptionArn': 'test_subscription_arn'}
        mock_sns_client.publish.return_value = {}

        # Sample payload
        payload = {
            'request_id': '123',
            'manager_id': 6789,
            'staff_id': 12345,
            'full_name': 'Jane Doe',
            'request_type': 'approval'
        }

        response = self.app.post('/notifications/notify/staff', json=payload)

        # Check response status code and message
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json['message'], "Notification sent!")

        # Check if SNS and SQS methods were called
        mock_sqs_client.create_queue.assert_called_once_with(QueueName=f"{payload['staff_id']}_queue")
        mock_sns_client.subscribe.assert_called_once()
        mock_sns_client.publish.assert_called_once()

    def test_notify_staff_invalid_request_type(self):
        # Sample payload with invalid request type
        payload = {
            'request_id': '123',
            'manager_id': 6789,
            'staff_id': 12345,
            'full_name': 'Jane Doe',
            'request_type': 'invalid_type'
        }

        response = self.app.post('/notifications/notify/staff', json=payload)

        # Check response status code and message
        self.assertEqual(response.status_code, 500)
        self.assertIn("Error:", response.json['message'])

    def test_configure_message_to_staff_approval(self):
        data = {
            'request_id': 123,
            'manager_id': 6789,
            'staff_id': 12345,
            'full_name': 'Jane Doe',
            'request_type': 'approval'
        }

        message = configure_message_to_staff(data)

        # Check that the message is constructed correctly for approval
        expected_message = {
            'request_id': 123,
            'manager_id': 6789,
            'staff_id': 12345,
            'sender': 'Jane Doe',
            'message': 'Your WFH request ID: 123 is approved'
        }

        self.assertEqual(message, expected_message)

    def test_configure_message_to_staff_rejection(self):
        data = {
            'request_id': 456,
            'manager_id': 6789,
            'staff_id': 12345,
            'full_name': 'John Smith',
            'request_type': 'rejection'
        }

        message = configure_message_to_staff(data)

        # Check that the message is constructed correctly for rejection
        expected_message = {
            'request_id': 456,
            'manager_id': 6789,
            'staff_id': 12345,
            'sender': 'John Smith',
            'message': 'Your WFH request ID: 456 is rejected'
        }

        self.assertEqual(message, expected_message)
    
    @patch('notification.SQS_CLIENT')
    @patch('notification.SNS_CLIENT')
    def test_notify_staff_missing_fields(self, mock_sns_client, mock_sqs_client):
        # Sample payload with missing fields
        payload = {
            'manager_id': 6789,
            'staff_id': 12345,
            'full_name': 'Jane Doe',
            # Missing request_id and request_type
        }

        response = self.app.post('/notifications/notify/staff', json=payload)

        # Check response status code and message for KeyError
        self.assertEqual(response.status_code, 400)
        self.assertIn("Missing required field:", response.json['message'])

if __name__ == '__main__':
    unittest.main()
