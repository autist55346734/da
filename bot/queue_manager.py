import asyncio
import logging
from collections import deque
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RequestQueue:
    def __init__(self):
        self.queue = deque()
        self.processing = False
        self.bot = None
    
    def set_bot(self, bot):
        self.bot = bot
    
    async def add(self, user_id, callback, *args):
        position = len(self.queue) + 1
        self.queue.append({
            'user_id': user_id,
            'callback': callback,
            'args': args,
            'added_at': datetime.now()
        })
        if not self.processing:
            asyncio.create_task(self._process())
        return position
    
    async def _process(self):
        self.processing = True
        while self.queue:
            request = self.queue.popleft()
            try:
                result = await request['callback'](*request['args'])
                await self._send_message(request['user_id'], result)
            except Exception as e:
                await self._send_message(request['user_id'], f"❌ Ошибка: {e}")
            await asyncio.sleep(0.5)
        self.processing = False
    
    async def _send_message(self, user_id, message):
        if self.bot:
            try:
                if isinstance(message, dict):
                    msg = message.get('feedback', str(message))
                else:
                    msg = str(message)
                await self.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Ошибка отправки: {e}")

queue = RequestQueue()