import json
import asyncio
import logging
import pika
import signal
import sys
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor
from src.models import VideoCompilationJob

logger = logging.getLogger(__name__)

class QueueConsumer:
    def __init__(
        self,
        rabbitmq_url: str,
        queue_name: str,
        prefetch_count: int = 1,
        auto_reconnect: bool = True
    ):
        self.rabbitmq_url = rabbitmq_url
        self.queue_name = queue_name
        self.prefetch_count = prefetch_count
        self.auto_reconnect = auto_reconnect
        
        self.connection: Optional[pika.BlockingConnection] = None
        self.channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None
        self.is_consuming = False
        self.job_handler: Optional[Callable] = None
        
        # Thread pool for handling async job processing
        self.executor = ThreadPoolExecutor(max_workers=4)
        
    def connect(self) -> bool:
        """Establish connection to RabbitMQ"""
        try:
            # Parse connection parameters
            parameters = pika.URLParameters(self.rabbitmq_url)
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Set QoS for fair dispatch
            self.channel.basic_qos(prefetch_count=self.prefetch_count)
            
            # Ensure queue exists
            self.channel.queue_declare(queue=self.queue_name, durable=True)
            
            logger.info(f"Connected to RabbitMQ queue: {self.queue_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close RabbitMQ connection"""
        try:
            if self.channel and not self.channel.is_closed:
                self.channel.close()
            if self.connection and not self.connection.is_closed:
                self.connection.close()
            logger.info("Disconnected from RabbitMQ")
        except Exception as e:
            logger.error(f"Error disconnecting from RabbitMQ: {e}")
    
    def set_job_handler(self, handler: Callable) -> None:
        """Set the async handler function for processing jobs"""
        self.job_handler = handler
    
    def _process_message(self, channel, method, properties, body) -> None:
        """Process a single message from the queue"""
        try:
            # Parse the job data
            job_data = json.loads(body.decode('utf-8'))
            job = VideoCompilationJob(**job_data)
            
            logger.info(f"Received job for request: {job.request_id}")
            
            if self.job_handler:
                # Run the async job handler in the thread pool
                future = self.executor.submit(
                    asyncio.run,
                    self.job_handler(job)
                )
                
                # Wait for completion
                result = future.result()
                
                if result:
                    # Acknowledge the message
                    channel.basic_ack(delivery_tag=method.delivery_tag)
                    logger.info(f"Job completed for request: {job.request_id}")
                else:
                    # Reject and requeue on failure
                    channel.basic_nack(
                        delivery_tag=method.delivery_tag,
                        requeue=True
                    )
                    logger.error(f"Job failed for request: {job.request_id}, requeuing...")
            else:
                logger.error("No job handler set")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in message: {e}")
            channel.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(self) -> None:
        """Start consuming messages from the queue"""
        if not self.connection or not self.channel:
            if not self.connect():
                return
        
        try:
            self.is_consuming = True
            
            # Set up message consumer
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self._process_message
            )
            
            logger.info(f"Started consuming from queue: {self.queue_name}")
            
            # Start consuming
            while self.is_consuming:
                try:
                    self.connection.process_data_events(time_limit=1.0)
                except pika.exceptions.AMQPConnectionError:
                    if self.auto_reconnect:
                        logger.warning("Connection lost, attempting to reconnect...")
                        self.reconnect()
                    else:
                        break
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, stopping consumer...")
                    break
                    
        except Exception as e:
            logger.error(f"Error in consumer loop: {e}")
        finally:
            self.stop_consuming()
    
    def stop_consuming(self) -> None:
        """Stop consuming messages"""
        self.is_consuming = False
        if self.channel:
            self.channel.stop_consuming()
        logger.info("Stopped consuming messages")
    
    def reconnect(self) -> bool:
        """Reconnect to RabbitMQ"""
        try:
            self.disconnect()
            return self.connect()
        except Exception as e:
            logger.error(f"Error during reconnection: {e}")
            return False
    
    def health_check(self) -> bool:
        """Check if the queue consumer is healthy"""
        try:
            if not self.connection or self.connection.is_closed:
                return False
            if not self.channel or self.channel.is_closed:
                return False
            return True
        except Exception:
            return False

def setup_signal_handlers(consumer: QueueConsumer) -> None:
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        consumer.stop_consuming()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)