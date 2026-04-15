# 🤖 Telegram Automation Engine: Multi-Account Intelligent Distribution
### A Distributed System for AI-Driven Content Extraction & Real-Time Syncing

A scalable backend architecture designed to handle high-concurrency Telegram operations, featuring intelligent data extraction via Gemini AI and real-time click analytics.

---

## 🛠️ Engineering Architecture

This project is built as a **distributed automation pipeline**:
1.  **Orchestrator (GitHub Actions):** Schedules high-frequency data extraction from Amazon and other sources.
2.  **Intel Engine (Gemini AI):** Processes unstructured HTML data into structured JSON, filtering for high-value metrics and real-time discounts.
3.  **Local Worker Node (Laptop Agent):** Handles session-persistent operations (Telethon) to manage multi-account forwarding and contact-based promotion.
4.  **Analytics Layer (Netlify Serverless):** Tracks user engagement through a performant redirect-and-count system using Netlify Blobs.

---

## 🚀 Key Technical Features

- **Multi-Account Concurrency:** Manages multiple Telethon sessions simultaneously to bypass rate limits and improve reach.
- **AI-Driven Extraction:** Custom prompt engineering for Gemini AI to extract product details from complex, dynamic HTML content.
- **Session Persistence:** State-aware worker scripts that maintain long-running user sessions for secure automated operations.
- **Real-time Analytics:** Custom-built click-tracking redirector with historical data storage on Netlify serverless infrastructure.

---

## 📂 Project Structure

- `auto_forwarder.py`: High-concurrency worker for multi-channel message distribution.
- `trending_updater.py`: Automated orchestration script for scraping and content generation.
- `bot_post.py`: Intelligent message generator with templating and price-tracking logic.
- `netlify-redirector/`: Serverless functions for high-performance link tracking and analytics.
- `fetch_contacts.py`: Tooling for contact graph extraction across multiple accounts.

---

## ⚙️ Tech Stack

- **Lanuage:** Python 3.10+
- **APIs:** Telegram Telethon, Gemini AI API, Telegram Bot API
- **Cloud:** GitHub Actions (CI/CD), Netlify (Serverless Functions & Blobs)
- **Data:** JSON-based state management, local session persistence

---
*Created by [Shashwat Srivastava](https://github.com/Shashwat1319)* | [LinkedIn](https://www.linkedin.com/in/shashwatsrivastava131/) | [Portfolio](https://shashwat-srivastava.netlify.app)
