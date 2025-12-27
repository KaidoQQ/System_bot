# 🖥️ Smart PC Builder Bot

A Telegram bot designed to help users plan, price, and validate custom PC builds. It utilizes a local **SQLite** database for component management and integrates **Google Gemini AI** to analyze build compatibility and provide expert recommendations.

## ✨ Features

* **🛠️ Interactive Build System:** Create and manage multiple PC builds simultaneously.
* **💾 Auto-Save & Database:** All progress is automatically saved to a local SQLite database (`computers.db`). Users can pause and resume building at any time.
* **🔍 Smart Search:** Search for components (CPU, GPU, RAM, etc.) by name using a relevance scoring algorithm.
* **💰 Automatic Pricing:** Calculates the total cost of the build in real-time.
* **✍️ Manual Entry:** Allows users to manually enter component names and prices if they are not found in the database.
* **🤖 AI Integration:** Uses **Google Gemini Flash latest version** to analyze the completed build, identify bottlenecks, and rate compatibility (1-10).

## 🚀 Tech Stack

* **Language:** Python 3.10+
* **Bot Framework:** `pyTelegramBotAPI` (telebot)
* **Database:** SQLite3
* **AI Service:** Google Generative AI (`google-genai`)
* **Data Format:** JSON (internal logic), CSV (price imports)

## 📂 Project Structure

```text
├── System_bot/
│   │── system_bot.py      # Main bot application logic
│   │── parsing.py         # Automatization with BeautifulSoup
│   └── app.py             # Page where you can check all your setups
├── components.csv         # Database source for component prices
├── computers.db           # SQLite database (generated automatically)
├── .gitignore             # Git configuration to hide secrets
└── README.md              # Project documentation
```

## ⚙️ Installation & Setup

### 1. Clone the repository
```bash
git clone [https://github.com/KaidoQQ/System_bot.git](https://github.com/KaidoQQ/System_bot.git)
cd System_bot
```

### 2. Install dependencies
```bash
pip install pyTelegramBotAPI google-genai beautifulsoup4
```

### 3. Configure API Keys
Open `system_bot.py` and insert your API keys:
* **Telegram Bot Token:** Get it from [@BotFather](https://t.me/BotFather).
* **Google Gemini API Key:** Get it from [Google AI Studio](https://aistudio.google.com/).

### 4. Run the Bot
```bash
python System_bot/system_bot.py
```

## 🎮 Usage

1. Start the bot with the `/start` command.
2. Click **"🖥️ Create new system"** and name your build.
3. Use **"🔧 Add components"** to search for parts (e.g., type "RTX 4060" or "Intel i5").
4. Select a component from the list or use **"Enter manually"**.
5. Once all 5 core components (CPU, RAM, GPU, Storage, Motherboard) are added, click **"🎉 Build Complete!"**.
6. Click **"🤖 Check with AI"** to get an instant compatibility report.

## 🔜 Roadmap

- [x] Basic Build Management
- [x] SQLite Database Integration
- [x] AI Compatibility Check (Gemini)
- [x] **Web Dashboard:** A Flask-based web interface for viewing user statistics.
- [x] Automatization.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---
*Created by [KaidoQQ](https://github.com/KaidoQQ)*
