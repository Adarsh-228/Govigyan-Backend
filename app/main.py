import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse

from app.api.routes.erp_inventory import router as erp_inventory_router
from app.api.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url=None,
)

logger = logging.getLogger("app.request")
if not logger.handlers:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")

allow_all_origins = settings.cors_origins_list == ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info("%s %s -> %s (%sms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


@app.get("/docs", include_in_schema=False)
async def custom_swagger_docs() -> HTMLResponse:
    html = get_swagger_ui_html(
        openapi_url=app.openapi_url,
        title=f"{settings.APP_NAME} - API Docs",
        swagger_ui_parameters={
            "syntaxHighlight.theme": "obsidian",
            "tryItOutEnabled": True,
        },
    )
    custom_style = """
    <style>
      body { background: #0b1220 !important; }
      .swagger-ui .topbar { background: #111827 !important; border-bottom: 1px solid #1f2937; }
      .swagger-ui .info, .swagger-ui .scheme-container { background: #0f172a !important; color: #e5e7eb !important; }
      .swagger-ui .opblock { background: #111827 !important; border-color: #1f2937 !important; }
      .swagger-ui .opblock-summary { border-color: #1f2937 !important; }
      .swagger-ui .responses-inner h4, .swagger-ui .responses-inner h5 { color: #e5e7eb !important; }
    </style>
    """
    html_text = html.body.decode("utf-8").replace("</head>", f"{custom_style}</head>")
    return HTMLResponse(content=html_text, status_code=200)


app.include_router(api_router, prefix=settings.API_PREFIX)
app.include_router(erp_inventory_router)
