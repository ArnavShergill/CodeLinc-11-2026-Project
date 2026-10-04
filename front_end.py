import tkinter as tk
from tkinter import scrolledtext, ttk

import AI_interact
import back_end

# Keys must match the shared LifeNeedsProfile contract exactly.
REQUIRED_FIELDS = [
    "annualIncome", "spouseAnnualIncome", "numberOfDependents", "childrenAges",
    "mortgageBalance", "otherDebt", "finalExpenses", "desiredAnnualIncome",
    "incomeReplacementYears", "collegeFundingNeed", "existingLifeInsurance",
    "availableAssets", "inflationRate", "investmentReturnRate",
]


class LifeMapApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LifeMap-AI")
        self.root.geometry("900x600")
        self.root.minsize(700, 500)

        self.profile = {}
        self.result = None

        self._build_layout()
        self._add_ai_message(
            "Hi, I'm here to help figure out your life insurance needs. "
            "Tell me a bit about your situation to get started -- for "
            "example, your income, dependents, or any debts."
        )

    # ---------- layout ----------

    def _build_layout(self):
        container = ttk.Frame(self.root, padding=10)
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=3)
        container.columnconfigure(1, weight=2)
        container.rowconfigure(0, weight=1)

        # Left side: chat
        chat_frame = ttk.Frame(container)
        chat_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        chat_frame.rowconfigure(0, weight=1)
        chat_frame.columnconfigure(0, weight=1)

        self.chat_log = scrolledtext.ScrolledText(
            chat_frame, wrap="word", state="disabled", font=("Segoe UI", 10)
        )
        self.chat_log.grid(row=0, column=0, sticky="nsew")
        self.chat_log.tag_config("user", foreground="#1a5fb4", justify="right")
        self.chat_log.tag_config("ai", foreground="#2b2b2b")
        self.chat_log.tag_config("system", foreground="#888888", font=("Segoe UI", 9, "italic"))

        entry_row = ttk.Frame(chat_frame)
        entry_row.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        entry_row.columnconfigure(0, weight=1)

        self.entry = ttk.Entry(entry_row, font=("Segoe UI", 10))
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self.entry.bind("<Return>", lambda e: self.send_message())

        self.send_btn = ttk.Button(entry_row, text="Send", command=self.send_message)
        self.send_btn.grid(row=0, column=1)

        # Right side: profile confirmation panel
        side_frame = ttk.LabelFrame(container, text="What we understood so far", padding=10)
        side_frame.grid(row=0, column=1, sticky="nsew")
        side_frame.columnconfigure(0, weight=1)
        side_frame.rowconfigure(0, weight=1)

        self.profile_box = tk.Listbox(side_frame, font=("Segoe UI", 9))
        self.profile_box.grid(row=0, column=0, sticky="nsew")

        self.result_label = ttk.Label(
            side_frame, text="", font=("Segoe UI", 10, "bold"), wraplength=220
        )
        self.result_label.grid(row=1, column=0, sticky="w", pady=(10, 0))

    # ---------- chat helpers ----------

    def _add_message(self, text, tag):
        self.chat_log.configure(state="normal")
        prefix = {"user": "You: ", "ai": "LifeMap: ", "system": ""}[tag]
        self.chat_log.insert("end", prefix + text + "\n\n", tag)
        self.chat_log.configure(state="disabled")
        self.chat_log.see("end")

    def _add_ai_message(self, text):
        self._add_message(text, "ai")

    def _add_user_message(self, text):
        self._add_message(text, "user")

    def _add_system_note(self, text):
        self._add_message(text, "system")

    def _refresh_profile_panel(self):
        self.profile_box.delete(0, "end")
        for field in REQUIRED_FIELDS:
            value = self.profile.get(field)
            shown = value if value is not None else "—"
            self.profile_box.insert("end", f"{field}: {shown}")

    # ---------- core flow ----------

    def send_message(self):
        message = self.entry.get().strip()
        if not message:
            return
        self.entry.delete(0, "end")
        self._add_user_message(message)
        self.send_btn.config(state="disabled")
        self.root.after(50, lambda: self._process_message(message))

    def _process_message(self, message):
        try:
            self.profile = AI_interact.extract_fields(message, self.profile)
        except Exception as e:
            self._add_system_note(f"(AI extraction error: {e})")
            self.send_btn.config(state="normal")
            return

        self._refresh_profile_panel()

        missing = AI_interact.next_missing_field(self.profile)
        if missing is not None:
            try:
                question = AI_interact.ask_for_field(missing)
            except Exception:
                question = f"Could you tell me your {missing}?"
            self._add_ai_message(question)
            self.send_btn.config(state="normal")
            return

        # Profile is complete -- hand off to the calculation layer.
        self._add_system_note("Profile complete. Calculating your result...")
        try:
            self.result = back_end.calculate(self.profile)
        except Exception as e:
            self._add_system_note(f"(Calculation error: {e})")
            self.send_btn.config(state="normal")
            return

        try:
            explanation = AI_interact.explain_result(self.result)
        except Exception as e:
            explanation = f"(Explanation error: {e})"

        self._add_ai_message(explanation)
        needed = self.result.get("additionalCoverageNeeded")
        if needed is not None:
            self.result_label.config(text=f"Additional coverage needed:\n${needed:,.0f}")

        self.send_btn.config(state="normal")


def front_end():
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    LifeMapApp(root)
    root.mainloop()


if __name__ == "__main__":
    front_end()