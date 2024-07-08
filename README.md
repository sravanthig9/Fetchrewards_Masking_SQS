## Fetch Rewards
#### Data Engineering Take Home: ETL off a SQS Queue
#### Reading messages from the queue:
Messages are read from the SQS queue using the boto3 client for SQS. The receive_message method is used to fetch up to 10 messages at a time from the specified queue URL.

    def process_messages():
        client = boto3.client('sqs', endpoint_url='http://localhost:4566')
        while True:
            messages = client.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=10)
            if 'Messages' not in messages:
                break
            # Process each message
			
#### Data structures used:
The data structures used include:
1. Dictionaries: For parsing JSON data from the SQS messages.
2. Lists: For collecting records to be inserted into the PostgreSQL database.
3. Tuples: For representing individual records in a format suitable for batch insertion.
```
    data = json.loads(message['Body'])  # Parse JSON data into a dictionary
    records_to_insert = []  # List to collect records for batch insertion
    record = (data['user_id'], data['device_type'], encrypted_ip, encrypted_device_id, data['locale'], app_version_int, current_date)  # Tuple for each record
```
#### Masking the PII data so that duplicate values can be identified:
PII data is masked using AES encryption with a fixed IV, ensuring that the same input value always produces the same encrypted output. This allows for consistent masking of identical PII values.



    def aes_encrypt(key, data, iv):
        aes = AES.new(key, AES.MODE_CBC, iv)
        block_size = AES.block_size
        padding = block_size - len(data) % block_size
        data += bytes([padding] * padding)
        encrypted = aes.encrypt(data)
        return base64.b64encode(encrypted).decode()
    
    encrypted_device_id = aes_encrypt(KEY, data['device_id'].encode(), IV)
    encrypted_ip = aes_encrypt(KEY, data['ip'].encode(), IV)
	
#### Strategy for connecting and writing to Postgres:
The strategy for connecting to PostgreSQL involves using the psycopg2 library. The connection is established once, and records are inserted in batches using the execute_values method for efficiency.


    conn = psycopg2.connect(DB_CONNECTION)
    cursor = conn.cursor()
    
    # Batch insert records
    execute_values(cursor, """
        INSERT INTO user_logins (user_id, device_type, masked_ip, masked_device_id, locale, app_version, create_date)
        VALUES %s
    """, records_to_insert)
    conn.commit()
	
#### Running the application:
The application is designed to run in a local environment using Docker containers. The Docker setup includes containers for LocalStack (to simulate AWS services) and PostgreSQL. The script itself can be executed as a standalone Python application.

#### Setting up the docker compose file
#### Docker Setup:
Docker yaml file docker_sqs-compose.yml
#### Yaml file contents:
Write the following code block and save as docker_sqs-compose.yml or download the provided file of the same name.

    version: "3.3"
    services:
      localstack:
        image: fetchdocker/data-takehome-localstack
        ports:
          - "4566:4566"
      postgres:
        image: fetchdocker/data-takehome-postgres
        ports:
          - "5432:5432"
		  
		  
#### Code for running:
    python3 sqs_datapipeline.py
	
#### Potential Improvements and Additional Features
- **Logging**: Integrate a logging framework to replace print statements for better monitoring and debugging.
- **Configuration Management**: Use environment variables or a configuration file to manage constants like database connection strings, queue URLs, and encryption keys.
- **Error Handling**: Enhance error handling to include retries for transient errors, especially for database and network operations.
- **Testing**: Implement unit tests and integration tests to ensure the correctness of each component.
- **Scalability**: Consider implementing multi-threading or parallel processing to handle a higher volume of messages.
- **Security**: Improve key management by using a secure vault or environment variable instead of hardcoding the key.
- **Deployment**: Create Docker images and use orchestration tools like Kubernetes for deployment in production environments.
#### How would you deploy this application in production?
#### To deploy this application in a production environment, you would follow these steps:
- **Dockerize the Application:** Create Docker images for the Python script and any other components (e.g., LocalStack, PostgreSQL). This encapsulates the application and its dependencies.
- **Use Docker Compose or Kubernetes:** Use Docker Compose for simpler deployments or Kubernetes for more complex, scalable deployments. These tools manage the deployment, scaling, and management of containerized applications.
- **CI/CD Pipeline:** Set up a Continuous Integration/Continuous Deployment (CI/CD) pipeline using tools like Jenkins, GitHub Actions, or GitLab CI. This pipeline should automate the building, testing, and deployment of Docker images.
- **Environment Configuration:** Store sensitive information like database credentials and encryption keys in environment variables or a secure vault (e.g., AWS Secrets Manager, HashiCorp Vault).
- **Monitoring and Logging:** Integrate monitoring (e.g., Prometheus, Grafana) and logging (e.g., ELK stack) solutions to track the application's performance and troubleshoot issues.
- **Security:** Ensure the environment is secure by implementing network security groups, firewalls, and encrypted communication channels (e.g., SSL/TLS).
#### What other components would you want to add to make this production ready?
- **Logging Framework:** Implement a logging framework (e.g., Log4j, Python's logging module) for better log management.
- **Health Checks:** Add health checks for the application and its components to ensure they are running as expected.
- **Retry Mechanism:** Implement retry logic for transient failures, especially for network operations like SQS message retrieval and database connections.
- **Error Handling and Alerts:** Enhance error handling and integrate alerting mechanisms (e.g., PagerDuty) for critical failures.
- **Load Balancer:** Use a load balancer (e.g., AWS ALB) to distribute traffic evenly across instances.
- **Auto-Scaling:** Configure auto-scaling policies to handle varying loads by dynamically adjusting the number of running instances.
#### How can PII be recovered later on?
To recover PII, you can use the decryption function with the same encryption key and IV used for encryption. This requires secure storage and management of the encryption key and IV.


    def aes_decrypt(key, encrypted_data, iv):
    
        encrypted_data = base64.b64decode(encrypted_data)
        aes = AES.new(key, AES.MODE_CBC, iv)
        data = aes.decrypt(encrypted_data)
        padding = data[-1]
        return data[:-padding].decode()
    
    # Example usage
    encrypted_device_id = aes_encrypt(KEY, b'example_device_id', IV)
    decrypted_device_id = aes_decrypt(KEY, encrypted_device_id, IV)
    print(decrypted_device_id)
#### How can this application scale with a growing dataset?
- **Horizontal Scaling:** Deploy multiple instances of the application using container orchestration tools like Kubernetes. Use a load balancer to distribute the load evenly across instances.
- **Message Queue:** Use a managed message queue service (e.g., AWS SQS) to handle an increasing volume of messages. SQS scales automatically to accommodate the workload.
- **Database Optimization:** Optimize the PostgreSQL database with indexing, partitioning, and using read replicas to handle increased read loads.
- **Caching:** Implement caching mechanisms (e.g., Redis) to reduce the load on the database for frequently accessed data.

#### What are the assumptions you made?
- **Fixed IV for Deterministic Encryption:** Assumed that the use of a fixed IV for AES encryption is acceptable for this use case to ensure consistent masking of duplicate values.
- **Local Development Environment:** Assumed the application runs in a local environment using Docker containers for LocalStack and PostgreSQL.
- **Message Structure:** Assumed the structure of the messages in the SQS queue includes all required fields (user_id, device_id, ip, device_type, locale, app_version).
- **Error Handling:** Assumed that basic error handling with logging is sufficient for the scope of this example.
- **Simplified Version Handling:** Simplified version handling by removing periods and converting the result to an integer.
- **Security:** Assumed that the encryption key is securely managed and stored.

### Guide to run the project
We assume you have docker desktop setup, a linux machine and python3 with pip.
We are assuming that you will use ubuntu (preffered Ubuntu 18.04.6 LTS)
Please clone/copy the project files (docker_sqs-compose.yml and sqs_datapipeline.py) to your linux system.

    # first you do an apt update  
    sudo apt update
    #install pip if you dont have it
    sudo apt install python-pip
    #run the following 2 commands for running AWS CLI commands
    pip install awscli-local
    pip install awscli
    # run the following to enable postgres commands
    sudo apt install postgresql-client
    #get to the same folder as your docker compose file and run the following to start the containers
    cd your_path_to_compose_file
    docker-compose -f docker_sqs-compose.yml up -d
    #run the following to check if your containers are up and running
    docker ps
    #run the following command to check if your queue is working as expected
    awslocal sqs receive-message --queue-url http://localhost:4566/000000000000/login-queue
    #run the following to check if the postgres connection works and the table is present
    psql -d postgres -U postgres -p 5432 -h localhost -W
    postgres=# select * from user_logins;
    #Run the following to install psycopg2 to run the final code
     sudo apt-get install libpq-dev
     sudo pip install psycopg2
    # run the final code (go to the folder where your python file is present)
    python3 sqs_datapipeline.py
    

