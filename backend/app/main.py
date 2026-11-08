from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.routes.complaints import router as complaints_router
from backend.app.routes.analytics import router as analytics_router


app = FastAPI(
    title="YottaFlex Complaint Management API",
    description=(
        "Complaint classification, prioritization, assignment, "
        "SLA monitoring, resolution tracking and analytics."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:5173",
    "http://localhost:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "service": "YottaFlex Complaint Management API",
    }


app.include_router(complaints_router)
app.include_router(analytics_router)