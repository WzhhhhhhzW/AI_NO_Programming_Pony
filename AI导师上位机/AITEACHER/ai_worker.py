from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from config import get_endpoint_id


class AIWorker(QThread):
    response_received = pyqtSignal(str, bool, str)

    def __init__(self, client, messages, req_type="chat", model=None):
        super().__init__()
        self.client = client
        self.messages = messages
        self.req_type = req_type
        self.model = model if model else get_endpoint_id()

    def run(self):
        try:
            temp = 0.3 if self.req_type == "chat" else 0.7
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=temp,
            )
            reply = response.choices[0].message.content
            self.response_received.emit(reply, True, self.req_type)
        except Exception as e:
            self.response_received.emit(f"通信错误: {str(e)}", False, self.req_type)