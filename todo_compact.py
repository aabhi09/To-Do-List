# todo_compact.py
import json, os
from datetime import datetime

FILE = "todo.json"
DATE_FMT = "%Y-%m-%d"

class Task:
    def __init__(self, text, priority="medium", due=None, tag=""):
        self.text = text.strip()
        self.done = False
        self.priority = priority.lower()
        self.due = due.strip() if due else None
        self.tag = tag.strip().lower()
        self.created = datetime.now().strftime("%Y-%m-%d %H:%M")

    def __repr__(self):
        prio = {"high": "\033[31m[HIGH]\033[0m", "medium": "\033[33m[MED]\033[0m", "low": "\033[36m[LOW]\033[0m"}.get(self.priority, "[ ? ]")
        status = "\033[32m✔\033[0m" if self.done else " "
        due = f"  due {self.due}" if self.due else ""
        tag = f" \033[34m#{self.tag}\033[0m" if self.tag else ""
        overdue = " \033[31m(OVERDUE!)\033[0m" if self.due and not self.done and datetime.strptime(self.due, DATE_FMT).date() < datetime.now().date() else ""
        done_str = " (done)" if self.done else ""
        return f"{prio} [{status}] {self.text}{due}{overdue}{tag}{done_str}"

class Todo:
    def __init__(self):
        self.tasks = []
        self.load()

    def load(self):
        if os.path.exists(FILE):
            try:
                with open(FILE) as f:
                    self.tasks = [Task(**d) for d in json.load(f)]
            except:
                pass

    def save(self):
        with open(FILE, "w") as f:
            json.dump([vars(t) for t in self.tasks], f, indent=2)

    def show(self, pending=False):
        if not self.tasks:
            print("\n\033[33m→ Empty\033[0m\n")
            return
        print(f"\n\033[36m{'Pending' if pending else 'All'} Tasks:\033[0m")
        for i, t in enumerate(self.tasks, 1):
            if pending and t.done: continue
            print(f"{i:3}. {t}")

    def add(self):
        text = input("\033[36mTask: \033[0m").strip()
        if not text: return print("\033[31mEmpty\033[0m")
        t = Task(text)
        p = input("\033[36mPriority l/m/h [m]: \033[0m").strip().lower()
        t.priority = {"l":"low","h":"high"}.get(p[0] if p else "m", "medium")
        d = input("\033[36mDue yyyy-mm-dd: \033[0m").strip()
        if d:
            try: datetime.strptime(d, DATE_FMT); t.due = d
            except: print("\033[33mBad date → skipped\033[0m")
        t.tag = input("\033[36mTag: \033[0m").strip().lower()
        self.tasks.append(t)
        print("\033[32mAdded\033[0m")

    def mark(self):
        self.show()
        if not self.tasks: return
        try:
            i = int(input("\033[36mDone #: \033[0m")) - 1
            if 0 <= i < len(self.tasks):
                if not self.tasks[i].done:
                    self.tasks[i].done = True
                    print("\033[32mDone\033[0m")
                else:
                    print("\033[33mAlready done\033[0m")
        except:
            print("\033[31mInvalid\033[0m")

    def delete(self):
        self.show()
        if not self.tasks: return
        try:
            i = int(input("\033[36mDelete #: \033[0m")) - 1
            if 0 <= i < len(self.tasks):
                print(f"\033[32mDeleted: {self.tasks.pop(i).text}\033[0m")
        except:
            print("\033[31mInvalid\033[0m")

    def clear_done(self):
        n = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t.done]
        removed = n - len(self.tasks)
        print(f"\033[{'32mCleared '+str(removed) if removed else '33mNo completed'} tasks\033[0m")

    def run(self):
        print("\n\033[35mCompact To-Do\033[0m\n")
        while True:
            print(" 1 list   2 pending   3 add   4 done   5 del   6 clear   0 exit")
            c = input("\033[36m→ \033[0m").strip()
            if   c in ("1","l"): self.show()
            elif c in ("2","p"): self.show(True)
            elif c in ("3","a"): self.add()
            elif c in ("4","d"): self.mark()
            elif c in ("5","x"): self.delete()
            elif c == "6":       self.clear_done()
            elif c in ("0","q"): self.save(); print("\033[32mSaved. Bye!\033[0m"); break
            else: print("\033[33m?\033[0m")
            print()

if __name__ == "__main__":
    Todo().run()