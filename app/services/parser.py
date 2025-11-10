import pandas as pd
import pdfplumber
import io
import json
import logging
import re
from typing import Dict, Any, List

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def normalize_text(text: str) -> str:
    """Удаляет лишние пробелы и переносы строк из текста."""
    if not text:
        return ""
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def parse_xlsx(file_content: bytes) -> Dict[str, List[Dict[str, Any]]]:
    """
    Основной парсер для .xlsx файлов, использующий pandas.
    """
    try:
        xls = pd.ExcelFile(io.BytesIO(file_content))
        data = {}
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name)
            df_cleaned = df.fillna("").astype(str)
            data[sheet_name] = df_cleaned.to_dict(orient='records')
        logger.info("XLSX успешно распарсен с помощью pandas.")
        return data
    except Exception as e:
        logger.error(f"Ошибка парсинга XLSX с pandas: {e}", exc_info=True)
        raise ValueError("Не удалось обработать XLSX файл с помощью pandas.")

def parse_pdf(file_content: bytes) -> Dict[str, str]:
    """
    Основной парсер для .pdf файлов, использующий pdfplumber.
    """
    try:
        with pdfplumber.open(io.BytesIO(file_content)) as pdf:
            data = {}
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                data[f"page_{i+1}"] = normalize_text(text)
        logger.info("PDF успешно распарсен с помощью pdfplumber.")
        return data
    except Exception as e:
        logger.error(f"Ошибка парсинга PDF с pdfplumber: {e}", exc_info=True)
        raise ValueError("Не удалось обработать PDF файл с помощью pdfplumber.")

async def process_file(file_content: bytes, filename: str) -> Dict:
    """
    Обрабатывает файл, используя один, наиболее подходящий парсер в зависимости от типа файла.
    Шаг верификации удален для повышения надежности и скорости.
    """
    file_ext = filename.split('.')[-1].lower()
    logger.info(f"Начало обработки файла '{filename}' с расширением '{file_ext}'.")

    if file_ext in ['xlsx', 'xls']:
        processed_data = parse_xlsx(file_content)
    elif file_ext == 'pdf':
        processed_data = parse_pdf(file_content)
    else:
        raise ValueError(f"Неподдерживаемый тип файла: {file_ext}")

    logger.info(f"Файл '{filename}' успешно обработан.")
    return processed_data
