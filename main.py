from fastapi import FastAPI, Request, Form, Cookie, Response
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import httpx
import json
import aiosqlite
from datetime import datetime
import os

DEFAULT_DB_PATH = "weather.db"


async def init_db():
    db_path = getattr(app.state, "db_path", DEFAULT_DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS search_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                user_id TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass

app = FastAPI(lifespan=lifespan)


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


async def get_weather_data(city: str):
    async with httpx.AsyncClient() as client:
        geocoding_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1"
        response = await client.get(geocoding_url)
        data = response.json()
        
        if not data.get("results"):
            return None
            
        location = data["results"][0]
        lat, lon = location["latitude"], location["longitude"]
        

        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&hourly=temperature_2m,weather_code&timezone=auto"
        response = await client.get(weather_url)
        weather_data = response.json()
        
        return {
            "city": location["name"],
            "country": location.get("country", ""),
            "current": weather_data["current"],
            "hourly": {
                "time": weather_data["hourly"]["time"][:24],
                "temperature": weather_data["hourly"]["temperature_2m"][:24],
                "weather_code": weather_data["hourly"]["weather_code"][:24]
            }
        }

@app.get("/")
async def home(request: Request, last_city: str | None = Cookie(default=None)):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"last_city": last_city}
    )

@app.post("/search")
async def search_weather(
    request: Request,
    city: str = Form(...),
    user_id: str | None = Cookie(default=None)
):
   
    if not user_id:
        user_id = os.urandom(16).hex()
    
    weather_data = await get_weather_data(city)
    if not weather_data:
        return JSONResponse(
            content={"error": "Город не найден"},
            status_code=404
        )
    
   
    db_path = getattr(app.state, "db_path", DEFAULT_DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO search_history (city, user_id) VALUES (?, ?)",
            (city, user_id)
        )
        await db.commit()
    
    response = JSONResponse(content=weather_data)
    response.set_cookie(key="last_city", value=city, max_age=2592000)  # 30 days
    response.set_cookie(key="user_id", value=user_id, max_age=31536000)  # 1 year
    
    return response

@app.get("/cities/autocomplete")
async def autocomplete(q: str):
    if len(q) < 2:
        return []
    
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"https://geocoding-api.open-meteo.com/v1/search?name={q}&count=5"
        )
        data = response.json()
        if not data.get("results"):
            return []
        
        return [
            {
                "name": f"{city['name']}, {city.get('country', '')}",
                "latitude": city["latitude"],
                "longitude": city["longitude"]
            }
            for city in data["results"]
        ]

@app.get("/stats")
async def get_stats():
    db_path = getattr(app.state, "db_path", DEFAULT_DB_PATH)
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT city, COUNT(*) as count
            FROM search_history
            GROUP BY city
            ORDER BY count DESC
        """)
        rows = await cursor.fetchall()
        return {"stats": [dict(row) for row in rows]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 
