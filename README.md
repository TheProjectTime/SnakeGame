# Classic Snake Game — Standalone Desktop Application

A sleek, modern arcade-style **Classic Snake Game** built in Python 3 using Pygame. It runs locally as a standalone desktop window on Windows without requiring any browser, web server, database, or internet connection.

---

## 🎮 Key Features

- **Standalone Desktop Window:** Opens in a clean 600 × 500 pixel window titled **"Classic Snake Game"**.
- **Modern Arcade Aesthetics:** Deep slate background with a subtle grid, vibrant neon-green snake with expressive eyes, and glossy red apples.
- **Responsive Controls:** Play with either the **Arrow Keys** or **WASD**.
- **Smart Anti-Reversal:** Prevents instantaneous 180° self-collisions from accidental reverse inputs.
- **Dynamic Speed Progression:** Movement speed gradually scales up as your score climbs (from 9 FPS up to 22 FPS).
- **Game Screens & States:**
  - **Start Screen:** Title banner, full controls guide, current high score, and pulsing "PRESS [SPACE] TO START" prompt.
  - **Playing Screen:** Active grid, real-time score, best score, speed level, and keyboard shortcuts hint.
  - **Pause Screen:** Press `P` anytime to pause the action and catch your breath.
  - **Game-Over Screen:** Final score summary, high-score notification, and instant restart with `SPACE` or quit with `ESC`.
- **Persistent High Score with SQLite:** Stored in a local SQLite database (`snake_scores.db`) so your high scores and records are safely preserved across play sessions.
- **Arcade Audio & Visual Feedback:** Includes floating `+10` popup text, particle bursts, brief crash shake, and lightweight procedural retro sounds (no external audio files needed).

---

## 📂 Project Structure

```text
SnakeGame/
├── main.py             # Main game logic, state machine, entities, and rendering
├── requirements.txt    # Pygame package dependency
├── snake_scores.db     # SQLite database storing high scores
├── dist/               # Standalone Windows executable directory
│   └── ClassicSnakeGame.exe
├── README.md           # Documentation, launch instructions, and .exe guide
└── venv/               # Local Python virtual environment
```

---

## 🚀 How to Run the Game Locally

### Quick Launch (Using the Configured Virtual Environment)

Open **PowerShell** or **Command Prompt** in this folder (`d:\Antigravity\SnakeGame`) and run:

```powershell
.\venv\Scripts\python.exe main.py
```

---

### Step-by-Step Setup from Scratch (For Any Windows Machine)

If you copy this folder to another computer or want to rebuild the environment:

1. **Verify Python 3 is installed:**
   ```powershell
   python --version
   ```
   *(Ensure Python 3.8 or newer is installed).*

2. **Create a virtual environment:**
   ```powershell
   python -m venv venv
   ```

3. **Activate the virtual environment:**
   - On PowerShell:
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   - On Command Prompt (cmd):
     ```cmd
     .\venv\Scripts\activate.bat
     ```

4. **Install Pygame:**
   ```powershell
   pip install -r requirements.txt
   ```

5. **Launch the game:**
   ```powershell
   python main.py
   ```

---

## 🕹️ Controls Guide

| Action | Primary Key | Secondary Key | Mouse Support |
|---|---|---|---|
| **Move Up** | `↑` (Up Arrow) | `W` | — |
| **Move Down** | `↓` (Down Arrow) | `S` | — |
| **Move Left** | `←` (Left Arrow) | `A` | — |
| **Move Right** | `→` (Right Arrow) | `D` | — |
| **Play / Play Again** | `SPACE` | `RETURN` / `R` | Click **PLAY NOW** button |
| **Pause / Resume** | `P` | `SPACE` (while paused) | Click **[⏸]** HUD button |
| **Restart Game** | `R` | `SPACE` (on game over) | Click **PLAY AGAIN** |
| **Toggle Mute / Sound** | `M` | — | Click **[🔊]** HUD button |
| **Quit Game** | `ESC` | Window Close `[X]` | — |

---

## 📦 How to Package as a Standalone Windows `.exe`

You can compile this game into a single `.exe` file that runs with a double-click on any Windows PC **without opening a terminal window** and without needing Python installed.

1. **Install PyInstaller in your virtual environment:**
   ```powershell
   .\venv\Scripts\pip.exe install pyinstaller
   ```

2. **Build the standalone executable:**
   ```powershell
   .\venv\Scripts\pyinstaller.exe --onefile --noconsole --name "ClassicSnakeGame" main.py
   ```
   - `--onefile`: Packages everything into a single `.exe`.
   - `--noconsole`: Hides the background black terminal window so only the game window appears.
   - `--name "ClassicSnakeGame"`: Names the executable `ClassicSnakeGame.exe`.

3. **Locate and run your `.exe`:**
   Your standalone application will be generated in the `dist/` folder:
   ```text
   SnakeGame/dist/ClassicSnakeGame.exe
   ```
   Double-click `ClassicSnakeGame.exe` to play immediately!

---

## 🏆 Scoring & Rules

- **Eating an Apple:** Awards **+10 points** and grows the snake by 1 segment.
- **Speed Increase:** Every 30 points, the snake's speed increases by 1 step, adding more excitement.
- **Walls:** Crashing into any outer boundary ends the game.
- **Self-Collision:** Crashing into your own body ends the game.
- **High Score:** Beating your best score automatically saves it to the SQLite database (`snake_scores.db`) and displays a celebratory record badge on the game-over screen.
