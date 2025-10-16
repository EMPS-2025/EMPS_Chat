from __future__ import annotations

import os

import chainlit as cl
import httpx

from app.chatbot.nlp import parse_message
from app.core.config import get_settings

settings = get_settings()
BACKEND_URL = os.getenv("BACKEND_URL", "http://backend:8000")


@cl.on_chat_start
async def start() -> None:
    await cl.Message(content="Hi! Ask me about DAM, GDAM or RTM prices. e.g. 'DAM price for 2024-08-01 0-8'.").send()


@cl.on_message
async def handle_message(message: cl.Message) -> None:
    params = parse_message(message.content)
    if "date" not in params and "month" not in params:
        await cl.Message(content="I couldn't find a date or month in your request. Try 'DAM 2024-08-01 0-8'.").send()
        return

    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30.0) as client:
        response = await client.get("/api/prices", params=params)

    if response.status_code != 200:
        detail = response.json().get("detail", "Unknown error")
        await cl.Message(content=f"Backend error: {detail}").send()
        return

    data = response.json()
    lines = [
        f"Market: {data['inputs']['market']}",
        f"Window: {data['inputs'].get('date') or data['inputs'].get('month')} {data['inputs']['start_hour']}–{data['inputs']['end_hour']}",
        f"Average price: {data['price_rs_per_mwh']:.2f} Rs/MWh ({data['price_rs_per_kwh']:.4f} Rs/kWh)",
        f"Data points: {data['count']}",
    ]
    if data.get("daily"):
        lines.append("Daily breakdown:")
        for stat in data["daily"]:
            lines.append(
                f" - {stat['trade_date']}: {stat['price_rs_per_mwh']:.2f} Rs/MWh over {stat['count']} blocks"
            )

    await cl.Message(content="\n".join(lines)).send()
