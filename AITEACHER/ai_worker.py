import time

from PyQt6.QtCore import QThread, pyqtSignal
from openai import OpenAI
from config import get_endpoint_id


class AIWorker(QThread):
    response_received = pyqtSignal(str, bool, str)
    chunk_received = pyqtSignal(str)

    def __init__(self, client, messages, req_type="chat", model=None):
        super().__init__()
        self.client = client
        self.messages = messages
        self.req_type = req_type
        self.model = model if model else get_endpoint_id()

    def run(self):
        try:
            temp = 0.3 if self.req_type == "chat" else 0.7
            if self.req_type in ("concept", "guide"):
                stream = self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    temperature=temp,
                    stream=True,
                )
                chunks = []
                pending = []
                last_emit = time.monotonic()
                for event in stream:
                    if self.isInterruptionRequested():
                        stream.close()
                        return
                    if not event.choices:
                        continue
                    content = event.choices[0].delta.content
                    if content:
                        chunks.append(content)
                        pending.append(content)
                        now = time.monotonic()
                        if now - last_emit >= 0.08:
                            self.chunk_received.emit("".join(pending))
                            pending.clear()
                            last_emit = now
                if pending:
                    self.chunk_received.emit("".join(pending))
                self.response_received.emit("".join(chunks), True, self.req_type)
                return
            response = self.client.chat.completions.create(
                model=self.model,
                messages=self.messages,
                temperature=temp,
            )
            reply = response.choices[0].message.content
            self.response_received.emit(reply, True, self.req_type)
        except Exception as e:
            self.response_received.emit(f"通信错误: {str(e) or type(e).__name__}", False, self.req_type)
