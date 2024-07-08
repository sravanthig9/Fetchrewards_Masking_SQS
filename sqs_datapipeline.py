import boto3
import psycopg2
import json
from datetime import datetime
from Crypto.Cipher import AES
import hashlib
import base64
from psycopg2.extras import execute_values

# Setup boto3 for LocalStack with dummy credentials
boto3.setup_default_session(
    aws_access_key_id='fakeMyKeyId',
    aws_secret_access_key='fakeSecretAccessKey',
    region_name='us-east-1'
)

# Constants for the task
KEY = hashlib.sha256(b'secret_key').digest()  # Example key derived from a passphrase
IV = b'16charslongiv!!!'  # 16 bytes fixed IV, must be the same for encryption/decryption
QUEUE_URL = "http://localhost:4566/000000000000/login-queue"
DB_CONNECTION = "dbname='postgres' user='postgres' host='localhost' password='postgres' port='5432'"
REQUIRED_FIELDS = ['user_id', 'device_id', 'ip', 'device_type', 'locale', 'app_version']

# AES Encryption and Decryption
def aes_encrypt(key, data, iv):
    aes = AES.new(key, AES.MODE_CBC, iv)
    block_size = AES.block_size
    padding = block_size - len(data) % block_size
    data += bytes([padding] * padding)
    encrypted = aes.encrypt(data)
    return base64.b64encode(encrypted).decode()

def aes_decrypt(key, encrypted_data, iv):
    encrypted_data = base64.b64decode(encrypted_data)
    aes = AES.new(key, AES.MODE_CBC, iv)
    data = aes.decrypt(encrypted_data)
    padding = data[-1]
    return data[:-padding].decode()

# Function to convert version string to an integer
def version_to_int(version_string):
    try:
        return int(version_string.replace('.', ''))
    except (ValueError, IndexError):
        print(f"Error converting version string: {version_string}")
        return 0  # Default to 0 on conversion failure

# Function to check if all required fields are present
def all_required_fields_present(data, required_fields):
    return all(field in data for field in required_fields)

# Function to process messages from the queue
def process_messages():
    client = boto3.client('sqs', endpoint_url='http://localhost:4566')
    conn = psycopg2.connect(DB_CONNECTION)
    cursor = conn.cursor()

    while True:
        messages = client.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10)
        if 'Messages' not in messages:
            break

        records_to_insert = []
        for message in messages['Messages']:
            data = json.loads(message['Body'])

            # Check for all required fields before processing
            if not all_required_fields_present(data, REQUIRED_FIELDS):
                print(f"Skipping message due to missing required fields: {message['MessageId']}")
                continue

            # Encrypt the PII fields
            encrypted_device_id = aes_encrypt(KEY, data['device_id'].encode(), IV)
            encrypted_ip = aes_encrypt(KEY, data['ip'].encode(), IV)

            # Get the current date
            current_date = datetime.now().date()

            # Handle app_version safely, converting to integer
            app_version_int = version_to_int(data.get('app_version', '0'))

            # Flatten JSON and prepare for database insertion
            record = (
                data['user_id'],
                data['device_type'],
                encrypted_ip,
                encrypted_device_id,
                data['locale'],
                app_version_int,
                current_date
            )
            records_to_insert.append(record)

            # Delete the message from the queue
            client.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message['ReceiptHandle'])

        # Insert records into the database
        try:
            execute_values(cursor, """
                INSERT INTO user_logins (user_id, device_type, masked_ip, masked_device_id, locale, app_version, create_date)
                VALUES %s
            """, records_to_insert)
            conn.commit()
        except Exception as e:
            print(f"Failed to insert records into database: {e}")
            conn.rollback()

    cursor.close()
    conn.close()

if __name__ == "__main__":
    process_messages()