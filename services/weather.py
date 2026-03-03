import requests
from datetime import datetime
from constants import WEATHER_API_URL
from config import WEATHER_API_KEY
import logging

logger = logging.getLogger(__name__)

def fetch_weather_for_llm(city: str, days: int = 1) -> dict:
    """
    Fetch full weather data from WeatherAPI
    Build a compact payload that will be sent to the LLM
    """

    params = {
        "key": WEATHER_API_KEY,
        "q": city,
        "days": days,
        "aqi": "no",
        "alerts": "no",
    }

    r = requests.get(WEATHER_API_URL, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    forecast_day = data["forecast"]["forecastday"][0]
    day = forecast_day["day"]
    hourly_list = []

    for h in forecast_day.get("hour", []):
        hourly_list.append({

            # Local time of this hour
            # format: YYYY-MM-DD HH:MM (24h)
            "time": h["time"],

            # Temperature at this hour
            "temp_c": h["temp_c"],

            # Weather condition text
            # ex: Sunny, Rain, Cloudy
            "condition": h["condition"]["text"],

            # Rain amount in mm
            "precip_mm": h.get("precip_mm"),

            # 1 = rain expected, 0 = no rain
            "will_it_rain": h.get("will_it_rain"),

            # chance of rain %
            "chance_of_rain": h.get("chance_of_rain"),

            # humidity %
            "humidity": h.get("humidity"),

            # wind speed
            "wind_kph": h.get("wind_kph"),
        })

    # -------------------------
    # Final payload sent to LLM
    # -------------------------

    llm_payload = {

        # =====================
        # Location info
        # =====================
        "location": {

            # City name
            "name": data["location"]["name"],

            # Region / state
            "region": data["location"]["region"],

            # Country
            "country": data["location"]["country"],

            # Timezone id
            "tz_id": data["location"]["tz_id"],

            # Current local time of the city
            # example: 2026-03-01 18:17
            "localtime": data["location"]["localtime"],
        },

        # =====================
        # Current weather now
        # =====================
        "current": {

            # last update time
            "last_updated": data["current"]["last_updated"],

            # current temperature
            "temp_c": data["current"]["temp_c"],

            # feels like temperature
            "feelslike_c": data["current"]["feelslike_c"],

            # current condition
            "condition": data["current"]["condition"]["text"],

            # humidity %
            "humidity": data["current"]["humidity"],

            # cloud %
            "cloud": data["current"]["cloud"],

            # wind speed
            "wind_kph": data["current"]["wind_kph"],

            # wind direction
            "wind_dir": data["current"]["wind_dir"],

            # rain amount now
            "precip_mm": data["current"]["precip_mm"],
        },

        # =====================
        # Today summary
        # =====================
        "today": {

            # date of forecast
            "date": forecast_day["date"],

            # overall condition today
            "condition": day["condition"]["text"],

            # max temp today
            "maxtemp_c": day["maxtemp_c"],

            # min temp today
            "mintemp_c": day["mintemp_c"],

            # avg temp today
            "avgtemp_c": day["avgtemp_c"],

            # total rain today
            "totalprecip_mm": day.get("totalprecip_mm"),

            # 1/0 if rain expected
            "daily_will_it_rain": day.get("daily_will_it_rain"),

            # chance of rain %
            "daily_chance_of_rain": day.get("daily_chance_of_rain"),

            # UV index
            "uv": day.get("uv"),

            # sunrise time
            "sunrise": forecast_day["astro"].get("sunrise"),

            # sunset time
            "sunset": forecast_day["astro"].get("sunset"),
        },

        # =====================
        # Hourly forecast
        # =====================
        "hourly": hourly_list
    }

    return llm_payload