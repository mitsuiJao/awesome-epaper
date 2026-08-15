from draw import Draw
from datetime import datetime
import calendar
import requestAPI
import google_calendar

class DrawCalendar():
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
        events = google_calendar.get_calendar_events(SERVICEACCOUNTFILE, CALENDAERID)
        x = 524
        y = 32
        event = events[0]
        for i, event in enumerate(events):
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))
            formatted = self.format_events(start, end)
            self.draw.text(str(int(formatted["sm"])), x, y, 2, align="c", width=2)
            # self.draw.text("12", x, y, 2, align="c", width=2)
            self.draw.text(str(int(formatted["sd"])), x+44, y+8, 3, align="c", width=2)
            if not formatted["et"]:
                self.draw.text(formatted["st"], x+116, y+16, 2)
            else:
                self.draw.text(formatted["st"], x+116, y, 2)
                self.draw.text(formatted["et"], x+148, y+16, 2)

            self.draw.text(event.get("summary"), x, y+40, 3)
            self.draw.line(x+44, y, 556, y+32, 2)
            if i != 4:
                self.draw.line(x, y+76, 780, y+76)

            y += 88

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