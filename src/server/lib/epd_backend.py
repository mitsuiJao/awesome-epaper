import os


class MockEPD:
    def init(self):
        pass

    def getbuffer(self, image):
        return image

    def display(self, blackbuf, redbuf):
        pass

    def Clear(self):
        pass

    def sleep(self):
        pass


def get_epd():
    if os.environ.get("EPD_MODE", "real") == "mock":
        return MockEPD()
    from waveshare_epd import epd7in5b_V2
    return epd7in5b_V2.EPD()
