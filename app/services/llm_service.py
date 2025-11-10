import os
import json
import logging
from typing import Dict, Any

import requests
from dotenv import load_dotenv
from openai import OpenAI

# Загрузка переменных окружения из .env файла
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Конфигурация клиента OpenRouter ---
# Ключ API и базовый URL берутся из переменных окружения
api_key = os.getenv("OPENROUTER_API_KEY")
base_url = "https://openrouter.ai/api/v1"

if not api_key:
    logger.error("Переменная окружения OPENROUTER_API_KEY не установлена.")
    raise ValueError("Необходимо установить OPENROUTER_API_KEY")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

# Путь к файлу с промптом
PROMPT_FILE_PATH = 'promt_for_llm'
# Плейсхолдер, который будет заменен в промпте. Должен точно совпадать с текстом в файле.
PROMPT_DATA_PLACEHOLDER = '[СЮДА БУДУТ ПОДСТАВЛЕНЫ ВЕРИФИЦИРОВАННЫЕ ДАННЫЕ В ФОРМАТЕ JSON]'


def read_prompt_template() -> str:
    """Читает и возвращает содержимое файла с шаблоном промпта."""
    try:
        with open(PROMPT_FILE_PATH, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        logger.error(f"Файл с промптом не найден по пути: {PROMPT_FILE_PATH}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при чтении файла с промптом: {e}")
        raise

async def generate_dashboard(verified_data: Dict[str, Any]) -> str:
    """
    Генерирует HTML-дашборд с помощью LLM на основе верифицированных данных.
    """
    logger.info("Начало генерации дашборда с помощью LLM...")
    try:
        # 1. Чтение шаблона промпта
        prompt_template = read_prompt_template()

        # 2. Инъекция данных в шаблон
        # Преобразуем верифицированный Python dict в строку формата JSON
        json_data_string = json.dumps(verified_data, ensure_ascii=False, indent=2)
        
        # Плейсхолдер из нового промпта
        placeholder = "[СЮДА БУДУТ ПОДСТАВЛЕНЫ ВЕРИФИЦИРОВАННЫЕ ДАННЫДЕ В ФОРМАТЕ JSON]"
        
        if placeholder not in prompt_template:
            # Добавим проверку и для старого плейсхолдера для обратной совместимости на всякий случай
            old_placeholder = "[СЮДА БУДУТ ПОДСТАВЛЕНЫ ВЕРИФИЦИРОВАННЫЕ ДАННЫЕ В ФОРМАТЕ JSON]"
            if old_placeholder in prompt_template:
                placeholder = old_placeholder
            else:
                error_msg = "Критическая ошибка: плейсхолдер для данных не найден в файле промпта."
                logger.error(error_msg)
                raise ValueError(error_msg)

        # Заменяем плейсхолдер на реальные данные
        final_prompt = prompt_template.replace(placeholder, json_data_string)
        
        logger.info("Данные успешно вставлены в шаблон промпта.")
        # Логируем начало и конец промпта для проверки (без самих данных, чтобы не засорять лог)
        logger.debug(f"Начало итогового промпта: {final_prompt[:200]}...")
        logger.debug(f"...Конец итогового промпта: {final_prompt[-200:]}")

        # 3. Запрос к LLM
        logger.info("Отправка запроса к модели x-ai/grok-4-fast...")
        completion = client.chat.completions.create(
            model="x-ai/grok-4-fast", # Установлено по вашему запросу
            messages=[
                {
                    "role": "user",
                    "content": final_prompt,
                },
            ],
            temperature=0.1, # Низкая температура для более предсказуемого результата
        )

        # 4. Возврат результата
        html_response = completion.choices[0].message.content
        
        # Логируем ответ от LLM, чтобы видеть, что именно она возвращает
        logger.info(f"Получен ответ от LLM: {html_response[:500]}...") # Логируем начало ответа
        
        # Очистка ответа от возможных "оберток"
        if html_response.strip().startswith("```html"):
            html_response = html_response.strip()[7:-3].strip()
        
        logger.info("Дашборд успешно сгенерирован.")
        return html_response

    except json.JSONDecodeError:
        logger.error("Ошибка декодирования JSON ответа от модели. Модель вернула некорректный или пустой ответ.", exc_info=True)
        raise ValueError("Модель ИИ вернула некорректный ответ. Пожалуйста, попробуйте снова.")
    except Exception as e:
        logger.error(f"Произошла ошибка при генерации дашборда: {e}", exc_info=True)
        raise ValueError(f"Не удалось сгенерировать дашборд. Ошибка: {e}")
