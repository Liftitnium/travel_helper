# Budget Trip Bot

A Telegram bot that automatically finds the cheapest weekend trips by scraping budget airline fares (Ryanair & Wizz Air) and pairing them with the cheapest hostel dorm beds (Hostelworld, with Booking.com as fallback).

## Features

- **On-demand search** — send `/search` to get the top 10 cheapest weekend trips from your airport
- **Destination filter** — `/search porto` to search a specific city
- **Daily alerts** — automatic morning scans that push a message only when prices drop
- **Per-user preferences** — departure airport, budget cap, alert toggle
- **Multi-airline** — combines Ryanair and Wizz Air, deduplicates by destination
- **Hostel fallback** — tries Hostelworld first, falls back to Booking.com

## Quick Start

### 1. Create your Telegram bot

Talk to [@BotFather](https://t.me/BotFather) on Telegram and create a new bot. Copy the token.

### 2. Configure

```bash
cp .env.example .env
# Edit .env and paste your TELEGRAM_BOT_TOKEN
```

### 3a. Run locally

```bash
pip install -r requirements.txt
python -m bot.main
```

> Requires Chrome/Chromium and a matching ChromeDriver installed. `webdriver-manager` handles ChromeDriver automatically if Chrome is present.

### 3b. Run with Docker (recommended)

```bash
docker compose up -d --build
```

Docker bundles Chrome so there's nothing extra to install.

## Bot Commands

| Command | Description |
|---|---|
| `/start` | Welcome message and usage guide |
| `/setorigin <IATA>` | Set departure airport (default: MAD) |
| `/search` | Top 10 cheapest weekend trips |
| `/search <city>` | Search a specific destination |
| `/alerts on\|off` | Toggle daily price-drop alerts |
| `/budget <amount>` | Max total trip budget in € (0 to clear) |
| `/help` | Show available commands |

## How It Works

1. Scrapes Ryanair and Wizz Air fare finders for the cheapest flights over the next 8 weeks (1–3 night trips only)
2. For each destination found, scrapes Hostelworld (then Booking.com as fallback) for the cheapest dorm beds matching the flight dates
3. Assembles trip packages (roundtrip flight + hostel × nights), sorts by total cost
4. Sends formatted results via Telegram with booking links

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | — | **Required.** Token from BotFather |
| `DEFAULT_ORIGIN` | `MAD` | Default departure airport IATA code |
| `SCAN_HOUR` | `8` | Hour (24h, CET) for daily scheduled scan |
| `MAX_RESULTS` | `10` | Number of trips to show per search |
| `DATE_RANGE_WEEKS` | `8` | How many weeks ahead to search |

## Project Structure

```
budget-trip-bot/
├── bot/
│   ├── main.py          # Telegram bot setup & command handlers
│   ├── scheduler.py     # APScheduler daily scan + search pipeline
│   └── formatter.py     # Formats trips into Telegram messages
├── scrapers/
│   ├── base.py          # Selenium setup, anti-detection, shared helpers
│   ├── ryanair.py       # Ryanair fare scraper
│   ├── wizzair.py       # Wizz Air fare scraper
│   ├── hostelworld.py   # Hostelworld scraper
│   └── booking.py       # Booking.com fallback scraper
├── models/
│   ├── flight.py        # Flight dataclass
│   ├── hostel.py        # Hostel dataclass
│   └── trip.py          # Combined trip package
├── db/
│   └── database.py      # SQLite: user prefs, result caching
├── config.py            # Env vars and constants
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Notes

- Scraping runs sequentially with random delays (2–5s) to avoid hammering sites
- The bot uses headless Chrome with anti-detection measures (randomized user agents, disabled automation flags)
- Selenium scraping is offloaded to a thread executor so it doesn't block the async Telegram bot
- All scrapers are wrapped in try/except — if one airline or hostel site fails, the rest continue
