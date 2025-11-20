# hangman_with_better_maximize.py
import random
import string
import tkinter as tk
from tkinter import ttk, messagebox

# ---------------- CONFIG ----------------
WORD_LIST = [
    "python","engineer","random","banana","laptop","computer","mouse","keyboard","monitor","internet",
    "network","battery","camera","bottle","airport","bicycle","blanket","candle","canyon","carrot",
    "castle","ceiling","desert","diamond","doctor","dolphin","dragon","eagle","engine","farmer",
    "feather","festival","garage","galaxy","garden","giraffe","glasses","guitar","hammer","harbor",
    "helmet","hotel","island","jacket","jelly","journal","kitchen","ladder","lantern","library",
    "magnet","marble","meadow","mirror","monkey","mountain","needle","ocean","orange","oven",
    "packet","palace","pancake","panda","parent","parrot","pepper","pharmacy","picnic","planet",
    "pocket","police","rabbit","rainbow","river","rocket","scissors","scooter","school","screen",
    "season","sensor","shovel","singer","soap","soldier","sponge","stadium","station","statue",
    "sweater","teacher","temple","theater","thunder","ticket","tomato","tunnel","valley","vanilla",
    "volcano","wallet","window","zipper","orchard","beacon","compass","raindrop","sunrise","footpath"
]

MAX_WRONG = 6
POINTS_WIN = 10
TURN_SECONDS = 45  # seconds per turn

# ---------------- ASCII ANIMATION FRAMES ----------------
ASCII_FRAMES = [
    r"""
     (\_/)
     (•_•)
     / >🌟   HANGMAN
    """,
    r"""
     (\_/)
     (•_•)
    <  \    HANGMAN
     / \ 
    """,
    r"""
     (\_/)
     (•_•)
     / \    HANGMAN
    ~~~~~
    """,
    r"""
     (\_/)
    (•_• )♪
     / \   HANGMAN
    """,
    r"""
     (\_/)
    ( •_•)
    /  >   HANGMAN
    """,
    r"""
     (\_/)
    ( •_•)✦
     / \   HANGMAN
    """
]

ANIM_INTERVAL_MS = 300  # animation frame interval

# ---------------- APP ----------------
class HangmanApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Hangman Game")

        # Try to maximize on start (Windows first, then general fallback)
        # IMPORTANT: do NOT call geometry AFTER maximizing — that cancels the maximize.
        try:
            # Windows
            self.state("zoomed")
        except Exception:
            try:
                # Some X11/GTK builds support -zoomed attribute
                self.attributes("-zoomed", True)
            except Exception:
                # As last resort, use fullscreen (user can escape with Esc)
                try:
                    self.attributes("-fullscreen", True)
                except Exception:
                    pass

        # Allow resizing and let layout managers handle sizing
        self.resizable(True, True)

        # Core game state
        self.players = []
        self.scores = {}
        self.current = 0
        self.round = 1
        self.max_rounds = None
        self.secret = ""
        self.hint = ""
        self.display = []
        self.guessed = set()
        self.wrong = 0

        # Timer
        self.time_left = TURN_SECONDS
        self.timer_id = None

        # ASCII animation
        self.anim_index = 0
        self.anim_id = None

        # Build UI pages (pack/grid-based for responsive layout)
        self._build_start_page()
        self._build_game_page()

        # Show start
        self.show_start_page()

        # Bind Escape to exit fullscreen if we set it earlier
        self.bind("<Escape>", self._exit_fullscreen_if_any)

    def _exit_fullscreen_if_any(self, event=None):
        # If in fullscreen attribute, turn it off so user can return to windowed mode
        try:
            if self.attributes("-fullscreen"):
                self.attributes("-fullscreen", False)
        except Exception:
            pass

    # ---------------- Start Page ----------------
    def _build_start_page(self):
        # Use a full-page frame that expands
        self.start_frame = ttk.Frame(self)
        self.start_frame.pack(fill="both", expand=True)

        # We'll center an inner frame so the contents stay centered but scale
        inner = ttk.Frame(self.start_frame, padding=20)
        inner.place(relx=0.5, rely=0.45, anchor="center")  # center-ish

        # Title
        title = ttk.Label(inner, text="HANGMAN GAME", font=("Segoe UI", 36, "bold"))
        title.pack(pady=(6, 12))

        # Animated ASCII label (monospace)
        self.ascii_label = tk.Label(inner, text="", font=("Courier New", 16), justify="center")
        self.ascii_label.pack(pady=(0, 10))

        # Short subtitle / instructions
        subtitle = ttk.Label(inner, text="Guess letters before time runs out!", font=("Segoe UI", 12))
        subtitle.pack(pady=(0, 12))

        # Round selector row
        rounds_row = ttk.Frame(inner)
        rounds_row.pack(pady=(4, 12))
        ttk.Label(rounds_row, text="Rounds:", font=("Segoe UI", 10)).pack(side="left", padx=(0, 6))
        self.rounds_choice = ttk.Combobox(rounds_row, values=["Unlimited", "5", "10"], state="readonly", width=10)
        self.rounds_choice.current(0)
        self.rounds_choice.pack(side="left")

        # Play button
        play_btn = ttk.Button(inner, text="PLAY", command=self.show_game_page, width=20)
        play_btn.pack(pady=(8, 6))

        # Start ASCII animation
        self._start_animation()

    def _start_animation(self):
        if self.anim_id is None:
            self._anim_step()

    def _anim_step(self):
        frame = ASCII_FRAMES[self.anim_index % len(ASCII_FRAMES)]
        self.ascii_label.config(text=frame)
        self.anim_index += 1
        self.anim_id = self.after(ANIM_INTERVAL_MS, self._anim_step)

    def _stop_animation(self):
        if self.anim_id is not None:
            try:
                self.after_cancel(self.anim_id)
            except Exception:
                pass
            self.anim_id = None

    def show_start_page(self):
        # ensure animation is running
        if self.anim_id is None:
            self._start_animation()
        # hide game page and show start
        self.game_frame.pack_forget()
        self.start_frame.pack(fill="both", expand=True)

    # ---------------- Game Page ----------------
    def _build_game_page(self):
        self.game_frame = ttk.Frame(self)

        # top area: controls & scoreboard on left, game area on right
        # Use grid for responsiveness
        self.game_frame.columnconfigure(0, weight=1, minsize=280)
        self.game_frame.columnconfigure(1, weight=3)
        self.game_frame.rowconfigure(0, weight=1)

        # Left panel: players & scoreboard
        left = ttk.Frame(self.game_frame, padding=10, relief="flat")
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)

        ttk.Label(left, text="Players (comma or newline):", font=("Segoe UI", 10)).grid(row=0, column=0, sticky="w")
        self.names_box = tk.Text(left, height=6, width=35)
        self.names_box.grid(row=1, column=0, pady=6, sticky="ew")

        row = ttk.Frame(left)
        row.grid(row=2, column=0, sticky="w", pady=(4,8))
        ttk.Button(row, text="Start", command=self.start_game).pack(side="left", padx=4)
        ttk.Button(row, text="Back", command=self._back_to_start).pack(side="left", padx=4)
        ttk.Button(row, text="Reset", command=self.reset_game).pack(side="left", padx=4)

        ttk.Label(left, text="Scoreboard", font=("Segoe UI", 11, "bold")).grid(row=3, column=0, sticky="w", pady=(8,0))
        self.score_list = tk.Listbox(left, height=18, font=("Courier New", 10))
        self.score_list.grid(row=4, column=0, sticky="nsew", pady=5)
        left.rowconfigure(4, weight=1)

        # Right panel: gameplay
        right = ttk.Frame(self.game_frame, padding=10, relief="flat")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)

        self.lbl_player = ttk.Label(right, text="Not started", font=("Segoe UI", 16, "bold"))
        self.lbl_player.grid(row=0, column=0, sticky="w")

        self.lbl_round = ttk.Label(right, text="", font=("Segoe UI", 10))
        self.lbl_round.grid(row=1, column=0, sticky="w", pady=(2,8))

        # Hint + Word
        info = ttk.Frame(right)
        info.grid(row=2, column=0, sticky="w", pady=6)
        info.columnconfigure(1, weight=1)
        ttk.Label(info, text="Hint:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_hint = ttk.Label(info, text="", font=("Segoe UI", 10))
        self.lbl_hint.grid(row=0, column=1, sticky="w", padx=6)

        ttk.Label(info, text="Word:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, pady=8, sticky="w")
        self.lbl_word = ttk.Label(info, text="", font=("Courier New", 28))
        self.lbl_word.grid(row=1, column=1, sticky="w")

        # Lives and timer
        life_frame = ttk.Frame(right)
        life_frame.grid(row=3, column=0, sticky="w", pady=(8,0))
        ttk.Label(life_frame, text="Lives:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.lbl_lives = ttk.Label(life_frame, text="", font=("Segoe UI", 12))
        self.lbl_lives.pack(side="left", padx=6)

        ttk.Label(life_frame, text="Timer:", font=("Segoe UI", 10, "bold")).pack(side="left", padx=(16, 6))
        self.lbl_timer = ttk.Label(life_frame, text="", font=("Segoe UI", 12))
        self.lbl_timer.pack(side="left")

        # Guessed letters
        status = ttk.Frame(right)
        status.grid(row=4, column=0, sticky="w", pady=(8,0))
        ttk.Label(status, text="Guessed:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, sticky="w")
        self.lbl_guessed = ttk.Label(status, text="", font=("Segoe UI", 10))
        self.lbl_guessed.grid(row=0, column=1, sticky="w", padx=6)

        # Letter Buttons (wraps automatically by grid)
        self.letter_buttons = {}
        letters_frame = ttk.Frame(right)
        letters_frame.grid(row=5, column=0, sticky="nsew", pady=10)
        # allow letters_frame to expand if window is large
        right.rowconfigure(5, weight=1)

        cols = 9
        for i, ch in enumerate(string.ascii_uppercase):
            b = ttk.Button(letters_frame, text=ch, width=4, command=lambda L=ch: self.guess(L))
            b.grid(row=i // cols, column=i % cols, padx=2, pady=2, sticky="nsew")
            self.letter_buttons[ch] = b
            # make buttons expand a little
            letters_frame.grid_columnconfigure(i % cols, weight=1)

        # Actions
        actions = ttk.Frame(right)
        actions.grid(row=6, column=0, pady=12, sticky="w")
        ttk.Button(actions, text="Skip Turn", command=self.skip_turn).pack(side="left", padx=4)
        ttk.Button(actions, text="Reveal Word", command=self.reveal_word).pack(side="left", padx=4)
        ttk.Button(actions, text="End Match Now", command=self.end_match_now).pack(side="left", padx=4)

    def _back_to_start(self):
        # stop timer when returning to start page
        self.stop_timer()
        # restart ASCII animation
        if self.anim_id is None:
            self._start_animation()
        self.game_frame.pack_forget()
        self.start_frame.pack(fill="both", expand=True)

    def show_game_page(self):
        # read round choice from start page combobox
        sel = self.rounds_choice.get()
        if sel == "Unlimited":
            self.max_rounds = None
        else:
            try:
                self.max_rounds = int(sel)
            except Exception:
                self.max_rounds = None

        # stop front-page animation
        self._stop_animation()

        self.start_frame.pack_forget()
        self.game_frame.pack(fill="both", expand=True)

    # ---------------- Game logic ----------------
    def start_game(self):
        raw = self.names_box.get("1.0", "end").strip()
        if not raw:
            messagebox.showinfo("Missing", "Enter at least one player.")
            return

        names = []
        for line in raw.splitlines():
            for part in line.split(","):
                if part.strip():
                    names.append(part.strip())

        if not names:
            messagebox.showinfo("Missing", "Enter at least one player.")
            return

        self.players = names
        self.scores = {p: 0 for p in self.players}
        self.current = 0
        self.round = 1

        self.update_scoreboard()
        self.new_turn()

    def new_turn(self):
        # check rounds limit
        if self.max_rounds is not None and self.round > self.max_rounds:
            self.finish_match()
            return

        self.secret = random.choice(WORD_LIST)
        self.hint = f"Length: {len(self.secret)}"
        self.display = ["_"] * len(self.secret)
        self.guessed = set()
        self.wrong = 0

        self.lbl_player.config(text=f"{self.players[self.current]}'s turn")
        self.lbl_round.config(text=f"Round {self.round}" + (f" / {self.max_rounds}" if self.max_rounds else ""))
        self.lbl_hint.config(text=self.hint)
        self._refresh_ui()
        self.enable_letters(True)
        self.start_timer()

    def _refresh_ui(self):
        self.lbl_word.config(text=" ".join(self.display).upper())
        self.lbl_guessed.config(text=", ".join(sorted(self.guessed)).upper() or "(none)")
        hearts = "♥ " * (MAX_WRONG - self.wrong)
        self.lbl_lives.config(text=hearts if hearts else "✖")
        self.update_scoreboard()

    def enable_letters(self, enable):
        state = "normal" if enable else "disabled"
        for b in self.letter_buttons.values():
            b.config(state=state)

    def guess(self, letter):
        L = letter.lower()
        if L in self.guessed:
            return

        self.guessed.add(L)
        self.letter_buttons[letter].config(state="disabled")

        if L in self.secret:
            for i, ch in enumerate(self.secret):
                if ch == L:
                    self.display[i] = L
            self._refresh_ui()
            if "_" not in self.display:
                self.win()
        else:
            self.wrong += 1
            self._refresh_ui()
            if self.wrong >= MAX_WRONG:
                self.lose()

    def win(self):
        self.stop_timer()
        player = self.players[self.current]
        self.scores[player] += POINTS_WIN
        messagebox.showinfo("Victory!", f"{player} guessed the word!\n+{POINTS_WIN} points")
        self.end_turn()

    def lose(self):
        self.stop_timer()
        player = self.players[self.current]
        messagebox.showinfo("Lost", f"{player} failed.\nThe word was '{self.secret}'")
        self.end_turn()

    def end_turn(self):
        self.enable_letters(False)
        # advance player
        self.current = (self.current + 1) % len(self.players)
        if self.current == 0:
            self.round += 1

        # check if match should finish
        if self.max_rounds is not None and self.round > self.max_rounds:
            self.finish_match()
        else:
            self.new_turn()

    # ----- Timer methods -----
    def start_timer(self):
        self.stop_timer()
        self.time_left = TURN_SECONDS
        self._tick()

    def _tick(self):
        self.lbl_timer.config(text=f"{self.time_left} s")
        if self.time_left <= 0:
            self.stop_timer()
            messagebox.showinfo("Time's up", f"Time expired! The word was '{self.secret}'")
            self.end_turn()
            return
        self.time_left -= 1
        self.timer_id = self.after(1000, self._tick)

    def stop_timer(self):
        if self.timer_id is not None:
            try:
                self.after_cancel(self.timer_id)
            except Exception:
                pass
            self.timer_id = None
        self.lbl_timer.config(text="")

    # ----- Controls -----
    def skip_turn(self):
        if not self.players:
            return
        if messagebox.askyesno("Skip", "Skip this player's turn? No points awarded."):
            self.stop_timer()
            self.end_turn()

    def reveal_word(self):
        if not self.secret:
            return
        messagebox.showinfo("Reveal", f"The word was: {self.secret}")
        self.stop_timer()
        self.end_turn()

    def end_match_now(self):
        if messagebox.askyesno("End match", "End the match now and show the winner?"):
            self.finish_match()

    # ----- Finish match -----
    def finish_match(self):
        # stop timer and disable input
        self.stop_timer()
        self.enable_letters(False)

        if not self.scores:
            messagebox.showinfo("Match ended", "No players/scores to show.")
            return

        max_score = max(self.scores.values())
        winners = [p for p, s in self.scores.items() if s == max_score]

        if len(winners) == 1:
            title = "Winner!"
            body = f"{winners[0]} wins with {max_score} points."
        else:
            title = "It's a tie!"
            body = f"Tied winners ({len(winners)} players) with {max_score} points:\n" + ", ".join(winners)

        body += "\n\nFinal scoreboard:\n"
        for name, pts in sorted(self.scores.items(), key=lambda kv: -kv[1]):
            body += f"{name}: {pts} pts\n"

        messagebox.showinfo(title, body)

        if messagebox.askyesno("New match", "Return to start page to play again?"):
            # reset state
            self.players = []
            self.scores = {}
            self.current = 0
            self.round = 1
            self.max_rounds = None
            self.names_box.delete("1.0", "end")
            self.score_list.delete(0, "end")
            self.show_start_page()

    def update_scoreboard(self):
        self.score_list.delete(0, "end")
        for name, pts in sorted(self.scores.items(), key=lambda kv: -kv[1]):
            self.score_list.insert("end", f"{name:<14} {pts:>3} pts")

    def reset_game(self):
        if messagebox.askyesno("Reset", "Clear players and scores?"):
            self.players = []
            self.scores = {}
            self.current = 0
            self.round = 1
            self.names_box.delete("1.0", "end")
            self.score_list.delete(0, "end")
            self._set_idle()

    def _set_idle(self):
        self.lbl_player.config(text="Not started")
        self.lbl_round.config(text="")
        self.lbl_hint.config(text="")
        self.lbl_word.config(text="")
        self.lbl_guessed.config(text="")
        self.lbl_lives.config(text="")
        self.lbl_timer.config(text="")
        self.enable_letters(False)

# ---------------- RUN ----------------
if __name__ == "__main__":
    app = HangmanApp()
    app.mainloop()
