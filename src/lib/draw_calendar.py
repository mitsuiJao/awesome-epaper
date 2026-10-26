from .draw import Draw
from datetime import datetime
import calendar
from . import requestAPI
from . import google_calendar
from . import google_tasks

class DrawCalendar():
    MAX_ROWS = 5

    def __init__(self):
        self.draw = Draw()
        self.now = datetime.now()
        self.y = self.now.year
        self.m = self.now.month
        self.d = self.now.day
        # self.y = 2025
        # self.m = 11
        # self.d = 14
        # self.now = datetime(self.y, self.m, self.d)


        calendar.setfirstweekday(calendar.SUNDAY)
        self.calendar = calendar.monthcalendar(self.y, self.m)
        self.holidaysdic, self.holidays = self.format_holidays()
        self.WEEK = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
        self.WEEKDAY = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]

    def generate(self):
        self.draw_days()
        self.draw_today()
        self.draw_events()
        self.draw.line(500, 0, 500, 480, 3)
        self.draw.line(0, 88, 500, 88, 3)
        return self.draw.to_bytes()

    def draw_days(self):
        y = 120
        for index, weekstr in enumerate(self.WEEK):
            if index == 0:
                self.draw.text(weekstr, 32, y, 3, self.draw.RED)
                #epd.imagered.large_text(weekstr, 32, y, 3, 0xff)
            else:
                self.draw.text(weekstr, 32+(index*64), y, 3, self.draw.BLACK)
                #epd.imageblack.large_text(weekstr, 32+(index*64), y, 3, 0x00)

        dy = 56
        weeklen = len(self.calendar)
        if weeklen == 6:
            dy = 48
        if weeklen == 4:
            dy = 64
            
        y += dy
        for i in self.calendar:
            x = 32
            for index, day in enumerate(i):
                if day == 0:
                    pass
                else:
                    if day == self.d:
                        fill = True
                    else:
                        fill = False
                        
                    if index == 0 or day in self.holidays[self.m-1]:
                        c = self.draw.RED
                    else:
                        c = self.draw.BLACK
                        
                    self.draw.text(f"{day:>2}", x, y, 3, c, fill, 4, 8)

                x += 64
            y += dy

    def draw_today(self):
        self.draw.text(f"{self.y//100}", 32, 28, 2)
        self.draw.text(f"{self.y%100}", 32, 48, 2)
        self.draw.text(f"{self.m}/{self.d} {self.WEEKDAY[datetime.isoweekday(self.now)%7]}", 88, 28, 5, align="c", width=9)
        # self.draw.text(f"{self.WEEKDAY[datetime.isoweekday(self.now)%7]}", 336, 28, 5)

    def draw_events(self):
        rows = self.collect_agenda()
        if not rows:
            return
        x = 524
        y = 32
        for i, row in enumerate(rows):
            self.draw.text(row["month"], x, y, 2, align="c", width=2)
            self.draw.text(row["day"], x+44, y+8, 3, align="c", width=2)
            if not row["et"]:
                self.draw.text(row["st"], x+116, y+16, 2)
            else:
                self.draw.text(row["st"], x+116, y, 2)
                self.draw.text(row["et"], x+148, y+16, 2)

            self.draw.text(row["title"], x, y+40, 3, row["color"])
            self.draw.line(x+44, y, 556, y+32, 2)
            if i != len(rows) - 1:
                self.draw.line(x, y+76, 780, y+76)

            y += 88

    def collect_agenda(self):
        today = self.now.strftime("%Y-%m-%d")
        items = []

        for event in google_calendar.get_calendar_events() or []:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            f = self.format_events(start, end)
            items.append(((max(start[:10], today), start[11:16]), {
                "month": str(int(f["sm"])),
                "day": str(int(f["sd"])),
                "st": f["st"],
                "et": f["et"],
                "title": event.get("summary") or "",
                "color": self.draw.BLACK,
            }))

        for task in google_tasks.get_tasks() or []:
            due = task.get("due", "")[:10]
            overdue = bool(due) and due < today
            if not due:
                key_date, month, day = "9999-12-31", "--", "--"
            elif overdue:
                key_date, month, day = today, str(self.m), str(self.d)
            else:
                key_date, month, day = due, str(int(due[5:7])), str(int(due[8:10]))
            items.append(((key_date, ""), {
                "month": month,
                "day": day,
                "st": "Task",
                "et": "",
                "title": task.get("title") or "",
                "color": self.draw.RED if overdue else self.draw.BLACK,
            }))

        items.sort(key=lambda item: item[0])
        return [row for _, row in items[:self.MAX_ROWS]]

    def format_events(self, start, end):
            result = {}
            start_parts = start.split('T')
            end_parts = end.split('T')
            
            start_date = start_parts[0]
            end_date = end_parts[0]

            result["sm"] = start_date[5:7]
            result["sd"] = start_date[8:10]
            result["em"] = end_date[5:7]
            result["ed"] = end_date[8:10]

            is_allday = len(start_parts) == 1
            
            if is_allday:
                result["st"] = "Allday"
                result["et"] = ""

                if int(result["sm"]) < self.m or (int(result["sm"]) == self.m and int(result["sd"]) < self.d):
                    result["sd"] = f"{self.d:02}"
                    result["sm"] = f"{self.m:02}"

            else:
                start_time = start_parts[1][:5]
                end_time = end_parts[1][:5]
                
                if start_date == end_date:
                    result["st"] = start_time + "~"
                    result["et"] = end_time
                else:
                    result["st"] = start_time + "~"
                    result["et"] = ""

            return result

    def format_holidays(self):
        url = f"https://holidays-jp.github.io/api/v1/{self.y}/datetime.json"
        tmp = requestAPI.request_API(url)
        result = [[] for _ in range(12)]
        for date in tmp.keys():
            d = datetime.fromtimestamp(int(date))
            result[d.month-1].append(d.day)

        return tmp, result


if __name__ == "__file__":
    c = DrawCalendar()
    c.generate()
    c.draw._save("image.png")