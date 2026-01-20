# Todolist.py
import json
import os
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
        prio_map = {
            "high":   "\033[31m[HIGH]\033[0m",
            "medium": "\033[33m[MED]\033[0m",
            "low":    "\033[36m[LOW]\033[0m"
        }
        prio = prio_map.get(self.priority, "[ ? ]")
        status = "\033[32m✔\033[0m" if self.done else " "
        due_str = f" due {self.due}" if self.due else ""
        tag_str = f" \033[34m#{self.tag}\033[0m" if self.tag else ""
        overdue = " \033[31m(OVERDUE!)\033[0m" if (
            self.due and not self.done and 
            datetime.strptime(self.due, DATE_FMT).date() < datetime.now().date()
        ) else ""
        done_str = " (done)" if self.done else ""
        return f"{prio} [{status}] {self.text}{due_str}{overdue}{tag_str}{done_str}"


class TodoList:
    def __init__(self):
        self.tasks = []
        self.load()

    def load(self):
        if os.path.exists(FILE):
            try:
                with open(FILE, encoding="utf-8") as f:
                    data = json.load(f)
                    self.tasks = [Task(**item) for item in data]
            except Exception:
                print("\033[31mError loading todo.json — starting empty\033[0m")

    def save(self):
        try:
            with open(FILE, "w", encoding="utf-8") as f:
                json.dump([vars(t) for t in self.tasks], f, indent=2)
        except Exception as e:
            print(f"\033[31mCould not save: {e}\033[0m")

    def show(self, pending_only=False):
        if not self.tasks:
            print("\n\033[33m→ No tasks yet\033[0m\n")
            return

        title = "Pending Tasks" if pending_only else "All Tasks"
        print(f"\n\033[36m{title}:\033[0m")
        shown = 0
        for i, task in enumerate(self.tasks, 1):
            if pending_only and task.done:
                continue
            print(f"{i:3}. {task}")
            shown += 1
        if shown == 0:
            print("  (none pending)")

    def add(self):
        text = input("\033[36mTask: \033[0m").strip()
        if not text:
            print("\033[31mTask cannot be empty\033[0m")
            return

        t = Task(text)

        p = input("\033[36mPriority (l/m/h) [m]: \033[0m").strip().lower()
        t.priority = {"l": "low", "h": "high"}.get(p[0] if p else "m", "medium")

        d = input("\033[36mDue date (yyyy-mm-dd) or empty: \033[0m").strip()
        if d:
            try:
                datetime.strptime(d, DATE_FMT)
                t.due = d
            except ValueError:
                print("\033[33mInvalid date format — skipped\033[0m")

        tag = input("\033[36mTag (optional): \033[0m").strip().lower()
        if tag:
            t.tag = tag

        self.tasks.append(t)
        print("\033[32mTask added\033[0m")

    def mark_done(self):
        self.show()
        if not self.tasks:
            return
        try:
            num = int(input("\033[36mMark task # as done: \033[0m")) - 1
            if 0 <= num < len(self.tasks):
                task = self.tasks[num]
                if task.done:
                    print("\033[33mAlready marked done\033[0m")
                else:
                    task.done = True
                    print("\033[32mMarked done\033[0m")
            else:
                print("\033[31mInvalid number\033[0m")
        except ValueError:
            print("\033[31mPlease enter a number\033[0m")

    def delete(self):
        self.show()
        if not self.tasks:
            return
        try:
            num = int(input("\033[36mDelete task #: \033[0m")) - 1
            if 0 <= num < len(self.tasks):
                removed = self.tasks.pop(num)
                print(f"\033[32mDeleted: {removed.text}\033[0m")
            else:
                print("\033[31mInvalid number\033[0m")
        except ValueError:
            print("\033[31mPlease enter a number\033[0m")

    def clear_completed(self):
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if not t.done]
        removed = before - len(self.tasks)
        if removed == 0:
            print("\033[33mNo completed tasks to clear\033[0m")
        else:
            print(f"\033[32mCleared {removed} completed task{'s' if removed > 1 else ''}\033[0m")

    def run(self):
        print("\n\033[35mTo-Do List (saved to todo.json)\033[0m\n")
        while True:
            print(" 1. List all     2. Pending only")
            print(" 3. Add task     4. Mark done")
            print(" 5. Delete task  6. Clear completed")
            print(" 0. Exit")
            choice = input("\033[36m-> \033[0m").strip()

            if choice in ("1", "l"):
                self.show(False)
            elif choice in ("2", "p"):
                self.show(True)
            elif choice in ("3", "a"):
                self.add()
            elif choice in ("4", "d"):
                self.mark_done()
            elif choice in ("5", "x"):
                self.delete()
            elif choice == "6":
                self.clear_completed()
            elif choice in ("0", "q", "exit"):
                self.save()
                print("\n\033[32mSaved. Goodbye!\033[0m\n")
                break
            else:
                print("\033[33mInvalid choice\033[0m")

            print()


if __name__ == "__main__":
    TodoList().run()
