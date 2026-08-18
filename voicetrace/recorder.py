from voicetrace.events import VoiceEvent
from typing import Any

class EventRecorder:
    def __init__(self, exporters: list[Any]):
        self.exporters = exporters

    def record(self, event: VoiceEvent):
        for exporter in self.exporters:
            exporter.export(event)