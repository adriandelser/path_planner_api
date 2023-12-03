import datetime
import logging
import time
import uuid
from abc import abstractmethod

from kombu import Connection, Exchange, Queue
from rest_framework import serializers

from app.settings import AMQP_CONNECTION

logger = logging.getLogger(__name__)


class AmqpMetaSerializer(serializers.Serializer):
    correlation_id = serializers.UUIDField()
    headers = serializers.JSONField()
    timestamp = serializers.DateTimeField()
    kwargs = serializers.JSONField(required=False)


class AmqpPublishSerializer(serializers.Serializer):
    meta = AmqpMetaSerializer(required=False)
    body = serializers.JSONField()


class SimpleClient:
    """A simple synchronous rabbitmq-kombu client interface."""

    def __init__(
        self,
        *,
        exchange_name: str,
        connection_url: str = None,
        topics: str = None,
        exchange_type: str = "topic",
        queue_name: str = None,
        routing_key: str = None,
        **kwargs,
    ):
        self.connection_url = connection_url or AMQP_CONNECTION
        self.exchange_name = exchange_name
        self.topics = topics
        self.routing_key = routing_key

        if topics is None:
            self.topics = f"{self.exchange_name}.*"
        self.exchange_type = exchange_type
        self.queue_name = queue_name
        if queue_name is None:
            self.queue_name = (
                f"{self.__class__.__name__}-"
                f"{self.exchange_type}-"
                f"{self.exchange_name}-"
                f"{self.topics}-"
            )

    def _connect_consumer(self):
        """Connect to Rabbitmq queue given configuration params.
        Returns
        -------

        """
        with Connection(self.connection_url) as conn:
            # Create an exchange
            exchange = Exchange(self.exchange_name, type=self.exchange_type)
            # Create a queue
            queue = Queue(self.queue_name, exchange, routing_key=self.topics)
            # Bind the queue to the exchange
            queue.bind(conn)

            # Subscribe to the queue
            with conn.Consumer(queue, callbacks=[self.on_message]):
                # Process messages
                while True:
                    conn.drain_events()

    def init_consumer(self, raise_exception=False):
        """Initialize connection to Rabbitmq
        Parameters
        ----------
        raise_exception: If false, will keep retrying to connect on any error
        every 5 s

        Returns
        -------

        """
        if raise_exception:
            self._connect_consumer()
            return
        while True:
            try:
                self._connect_consumer()
            except Exception as e:
                err = f"[CRITICAL] [CONNECTION BROKEN] {e}"
                logger.info(msg=err)
                time.sleep(5)

    def publish(
        self,
        message: dict,
        routing_key: str = None,
        correlation_id=None,
        headers: dict = None,
        timestamp: datetime.datetime = None,
        serializer: serializers.Serializer.__class__ = None,
    ):
        """Publish message to Rabbitmq exchange

        Parameters
        ----------
        message: message to publish
        routing_key: str
        correlation_id : uuid.UUID
        headers : Dict
        timestamp : datetime.datetime
        serializer: serializers.Serializer.__class__

        Returns
        -------

        """
        # the kwargs are used in the unit tests
        # so they are added to the message meta
        # to avoid unexpected data to be passed
        # into the message body
        if message_kwargs := message.get("kwargs", {}):
            message.pop("kwargs")

        # validate the data if serializer is provided
        if serializer is not None:
            serializer = serializer(data=message)
            serializer.is_valid(raise_exception=True)
            message = serializer.data

        # Add meta data for debugging messages
        meta_data = {
            "correlation_id": correlation_id or uuid.uuid4(),
            "headers": headers or {},
            "timestamp": timestamp or datetime.datetime.now(),
            "kwargs": message_kwargs,
        }
        amqp_message = AmqpPublishSerializer(
            data={
                "meta": meta_data,
                "body": message,
            }
        )
        amqp_message.is_valid(raise_exception=True)

        # finally, connect and publish a message
        with Connection(self.connection_url) as conn:
            exchange = Exchange(self.exchange_name, type=self.exchange_type)
            producer = conn.Producer(exchange=exchange, serializer="json")
            producer.publish(
                body=amqp_message.data,
                routing_key=routing_key or self.routing_key,
                retry=True,
                headers=headers,
            )
            conn.close()

    @staticmethod
    @abstractmethod
    def on_message(body, message):
        pass


class CeleryTaskRunner:
    """Runs a list of shared tasks with arguments provided to call function.
    Results are interpreted by on_success and on_error methods.
    May run as a celery task or synchronous task.
    """

    @staticmethod
    @abstractmethod
    def on_success(result, ack, *args, **kwargs):
        pass

    @staticmethod
    @abstractmethod
    def on_error(exc, ack, *args, **kwargs):
        pass

    @classmethod
    def _call_async(cls, task, *args, **kwargs):
        task.apply_async(
            args=args, kwargs=kwargs, link=cls.on_success, link_error=cls.on_error
        )

    @classmethod
    def _call(cls, task, *args, **kwargs):
        try:
            result = task(*args, **kwargs)
            cls.on_success(result, *args, **kwargs)
        except Exception as e:
            cls.on_error(e, *args, **kwargs)

    @classmethod
    def call(
        cls,
        tasks,
        message: dict,
        exec_async=False,
        serializer: serializers.Serializer.__class__ = None,
        **kwargs,
    ):
        """

        Parameters
        ----------
        tasks: tasks to execute given valid message and kwargs
        message: message (dict) to pass to functions
        exec_async: should the task be executed in celery
        serializer: serializer to make sure message is valid
        kwargs: additional kwargs

        Returns
        -------

        """
        if serializer is not None:
            data = dict()
            try:
                data["serializer"] = serializer(data=message)
                data["serializer"].is_valid(raise_exception=True)
                message = data["serializer"].data
            except Exception as e:
                cls.on_error(e, message=message, **data, **kwargs)
                return
        for task in tasks:
            if exec_async:
                cls._call_async(task, message=message, **kwargs)
            else:
                cls._call(task, message=message, **kwargs)
