from fastapi import FastAPI, Request, File, UploadFile, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import logging
import uuid
import os
from werkzeug.utils import secure_filename
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded


from services.parser import process_file
from services.llm_service import generate_dashboard

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация rate limiter-а
limiter = Limiter(key_func=get_remote_address, default_limits=["20/minute"])
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

templates = Jinja2Templates(directory="templates")

# Хранилище для отчетов
reports_storage = {}
MAX_FILE_SIZE = 15 * 1024 * 1024
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'pdf'}


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/report/{report_id}", response_class=HTMLResponse)
async def get_report(report_id: str):
    report_html = reports_storage.get(report_id)
    if not report_html:
        raise HTTPException(status_code=404, detail="Отчет не найден.")
    return HTMLResponse(content=report_html)

@app.post("/process-file/")
@limiter.limit("10/minute")
async def process_file_endpoint(
    request: Request,
    file: UploadFile | None = File(None),
    text_input: str | None = Form(None)
):
    """
    Принимает файл или текст, обрабатывает его и возвращает сгенерированный HTML-дашборд и ID отчета.
    """
    if not file and not text_input:
        raise HTTPException(status_code=400, detail="Необходимо предоставить файл или текст.")

    try:
        if file:
            if file.size > MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail="Файл слишком большой.")
            filename = secure_filename(file.filename)
            if filename.split('.')[-1] not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail="Неподдерживаемый тип файла.")
            
            logger.info(f"Получен файл: {filename}, тип: {file.content_type}")
            contents = await file.read()
            processed_data = await process_file(contents, filename)
            logger.info("Файл успешно обработан.")

        elif text_input:
            logger.info("Получен текст для обработки.")
            processed_data = {"source": "text_input", "content": text_input}
            logger.info("Текст успешно инкапсулирован в JSON.")
        
        else:
            raise HTTPException(status_code=400, detail="Не предоставлены данные для обработки.")

        logger.info("Генерация дашборда с помощью LLM...")
        html_dashboard = await generate_dashboard(processed_data)
        logger.info("Дашборд успешно сгенерирован.")

        report_id = str(uuid.uuid4())
        reports_storage[report_id] = html_dashboard

        return JSONResponse(content={"html": html_dashboard, "report_id": report_id})

    except ValueError as e:
        logger.error(f"Ошибка валидации или обработки: {e}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"Произошла непредвиденная ошибка: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Произошла внутренняя ошибка сервера. Попробуйте позже.")
