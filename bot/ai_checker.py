import logging
import aiohttp
import asyncio
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OllamaChecker:
    def __init__(self, model="codellama:7b"):
        self.model = model
        self.api_url = "http://localhost:11434/api/generate"
        self.available = False
        self._check_connection()
    
    def _check_connection(self):
        import socket
        try:
            with socket.create_connection(("localhost", 11434), timeout=1):
                self.available = True
                logger.info("Ollama подключен")
        except OSError:
            logger.warning("Ollama не запущен. Работаю без ИИ")
    
    async def _call(self, prompt, system=""):
        if not self.available:
            return None
        async with aiohttp.ClientSession() as session:
            try:
                data = {
                    "model": self.model,
                    "prompt": prompt,
                    "system": system,
                    "stream": False,
                    "options": {"temperature": 0.7, "num_predict": 400}
                }
                async with session.post(self.api_url, json=data, timeout=30) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        return result.get('response', '')
            except Exception as e:
                logger.error("Ошибка: " + str(e))
        return None
    
    async def check_code(self, code, task, topic):
        # Если нет Ollama - простая проверка
        if not self.available:
            return self._simple_check(code, task)
        
        # Простая инструкция для ИИ
        prompt = f"""Проверь код Python.

Тема: {topic}
Задание: {task}

Код:
{code[:1000]}

Ответь в формате:
Оценка: (0-100)
Правильно или нет: 
Что хорошо: 
Что плохо: 
Совет:"""
        
        response = await self._call(prompt)
        if response:
            return self._parse_response(response)
        return self._simple_check(code, task)
    
    def _parse_response(self, response):
        # Проверяем, правильный ли код
        is_correct = "правильно" in response.lower() and "неправильно" not in response.lower()
        
        # Ищем оценку
        score = 50
        match = re.search(r'(\d+)', response)
        if match:
            score = min(100, int(match.group(1)))
        
        # Формируем ответ
        text = "🤖 *Проверка кода:*\n\n" + response[:600]
        if is_correct:
            text += "\n\n✅ Молодец! Так держать!"
        else:
            text += "\n\n💪 Попробуй исправить ошибки и отправь снова!"
        
        return {'correct': is_correct, 'score': score, 'feedback': text}
    
    def _simple_check(self, code, task):
        """Простая проверка без ИИ"""
        text = "🔍 *Проверка кода:*\n\n"
        score = 50
        
        # Проверка синтаксиса
        try:
            compile(code, '<string>', 'exec')
            text += "✅ Синтаксис верный\n"
            score += 30
        except SyntaxError as e:
            text += f"❌ Ошибка: {e.msg}\n"
        
        # Проверка наличия print
        if 'print(' in code:
            text += "✅ Есть вывод (print)\n"
            score += 10
        
        # Проверка на if (если нужно по заданию)
        if 'if' in task.lower() and 'if' in code:
            text += "✅ Есть условие if\n"
            score += 15
        
        # Проверка на цикл (если нужно по заданию)
        if ('for' in task.lower() or 'while' in task.lower()) and ('for' in code or 'while' in code):
            text += "✅ Есть цикл\n"
            score += 15
        
        score = min(100, score)
        text += f"\n📊 Оценка: {score}/100"
        
        if score >= 70:
            text += "\n\n✅ Код выглядит хорошо!"
        else:
            text += "\n\n💪 Нужно доработать. Проверь синтаксис и логику."
        
        if not self.available:
            text += "\n\n💡 Установи Ollama для умной проверки: https://ollama.com"
        
        return {'correct': score >= 70, 'score': score, 'feedback': text}
    
    async def get_hint(self, topic, task, question=""):
        """Подсказка по заданию"""
        if not self.available:
            return self._simple_hint(task)
        
        prompt = f"""Дай короткую подсказку (2-3 предложения) как решить задание.

Тема: {topic}
Задание: {task}
Вопрос: {question}

НЕ ПИШИ ГОТОВЫЙ КОД. Только направь ученика."""
        
        response = await self._call(prompt)
        if response:
            return "💡 *Подсказка:*\n\n" + response + "\n\n✨ Попробуй еще раз!"
        return self._simple_hint(task)
    
    def _simple_hint(self, task):
        """Простая подсказка без ИИ"""
        if 'print' in task.lower():
            return "💡 Используй `print()` для вывода на экран\n\n✨ Попробуй!"
        if 'if' in task.lower():
            return "💡 Используй `if условие:` для проверки\n\n✨ Попробуй!"
        if 'for' in task.lower():
            return "💡 Используй `for i in range():` для цикла\n\n✨ Попробуй!"
        if 'while' in task.lower():
            return "💡 Используй `while условие:` для цикла\n\n✨ Попробуй!"
        if 'input' in task.lower():
            return "💡 Используй `input()` для ввода данных\n\n✨ Попробуй!"
        return "💡 Разбей задачу на маленькие шаги и решай постепенно.\n\n✨ Попробуй!"


# Создаём один экземпляр
_checker = None

def get_checker():
    global _checker
    if _checker is None:
        _checker = OllamaChecker()
    return _checker

# Главные функции для бота
async def check_code(code, task, topic):
    checker = get_checker()
    return await checker.check_code(code, task, topic)

async def get_hint(topic, task, question=""):
    checker = get_checker()
    return await checker.get_hint(topic, task, question)