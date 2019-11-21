from tools.log import logger


class Checkpoint:
    def __init__(self, length, chunks=4, msg='already processed'):
        self._length = length
        self._chunks = chunks
        self._msg = msg
        self._idx = 0
        self._checkpoints = [round(i * float(self._length) / self._chunks) for i in range(self._chunks + 1)]

    def __iter__(self):
        return self

    def __next__(self):
        self._idx += 1
        if self._idx > self._length:
            self._idx = 0
            raise StopIteration  # Done iterating.

        if self._idx in self._checkpoints:
            progress = round(float(self._idx * 100) / self._length)
            logger.info(f"{progress}% {self._msg}")
