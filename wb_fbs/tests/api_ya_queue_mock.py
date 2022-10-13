import json


class MockYAQueueClient:
    def __init__(self, aws_access_key_id, aws_secret_access_key):
        self.smth = None

    def _get_queue_url(self, queue_name):
        return ...

    def get_messages(
        self,
        queue_name,
        message_model=None,
        count_messages=10,
        wait_time_seconds=3,
        visibility_timeout=20,
        is_json=True,
    ) -> list[tuple[dict, str]]:
        """
        :param: queue_name - имя очереди
        :param: count_messages=10 - сколько сообщений в пачке
        :param: wait_time_seconds=0 - сколько ждать если очередь пустая
        :param: visibility_timeout=20 - сколько скрывать сообщения от других
        :param: is_json - необходимо ли тело сообщения преобразовать в json

        :return: [(тело сообщения: dict | str, id для удаления из очереди)]
        """
        if self.smth is None:
            return []
        return [(json.loads(self.smth), "1")]

    def ack(self, queue_name, id_message):
        """
        В данном случае ничего не требуется очищать, мы один раз помещаем заказ в очередь.
        """
        pass

    def send_message(self, queue_name, message: str):
        self.smth = message
