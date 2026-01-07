import time


class ScrapeMetrics:
    def __init__(self):
        self.total_urls = 0
        self.successful = 0
        self.failed = 0
        self.total_time = 0.0
        self.languages = {}
        self.translated = 0
        self._start_time = None

    def start_url(self):
        self._start_time = time.time()

    def end_url(self, success: bool, lang: str = "unknown", translated: bool = False):
        if self._start_time is None:
            return

        time_taken = time.time() - self._start_time
        self._start_time = None

        self.total_urls += 1
        self.total_time += time_taken

        self.languages[lang] = self.languages.get(lang, 0) + 1

        if translated:
            self.translated += 1

        if success:
            self.successful += 1
        else:
            self.failed += 1

    def summary(self):
        return {
            "urls_checked": self.total_urls,
            "successful": self.successful,
            "failed": self.failed,
            "avg_time_per_url": round(
                self.total_time / max(1, self.total_urls), 2
            ),
            "languages": self.languages,
            "translated_count": self.translated
        }
