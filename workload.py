# pylint:disable=unnecessary-lambda-assignment,import-error
from __future__ import annotations

import argparse
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pprint import pprint

import psutil


@dataclass
class Usage:
    stamp: str
    average_cpu_percent: float

    def to_str(self, delim: str = ','):
        return delim.join(str(elem) for elem in [
            self.stamp,
            round(self.average_cpu_percent, 2),
        ])


class Collector:
    def __init__(self,
                 interval: float,
                 duration: float,
                 silent: bool,
                 estimated_cpu_percent: float):
        self.timers: list[threading.Timer] = []
        self.interval: float = interval
        self.duration: float = duration * 60
        self.silent: bool = silent
        self.estimated_cpu_percent: float = estimated_cpu_percent
        self.last_usage = None

    def _stdout(self, *lines: str):
        if not self.silent:
            print(*lines)

    def start(self):
        try:
            start_time = time.time()
            for i in range(int(self.duration / self.interval + 1)):
                # cleanup
                for j in range(len(self.timers) - 1, -1, -1):
                    if not self.timers[j].is_alive():
                        self.timers.pop(j)
                # add new timer to collect cpu usage
                timer = threading.Timer(0.0, self.collect_usage)
                timer.start()
                self.timers.append(timer)
                # add new timer to load cpu
                timer = threading.Timer(0.0, self.load)
                timer.start()
                self.timers.append(timer)
                # sleep remained time
                time.sleep((start_time + (i + 1) * self.interval) - time.time())
        finally:
            # cancel all timers
            for timer in self.timers:
                timer.cancel()

    def collect_usage(self):
        # cpu & memory
        average_cpu_percent = psutil.cpu_percent(interval=None, percpu=False)
        # logging
        usage = Usage(
            stamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            average_cpu_percent=average_cpu_percent,
        )
        self.last_usage = usage
        self._stdout(usage.to_str(', '))

    def load(self):
        print(round(self.interval * (self.estimated_cpu_percent * 0.01), 2))
        end_time = time.time() \
            + round(self.interval * (self.estimated_cpu_percent * 0.01), 2)
        while time.time() <= end_time:
            _ = sum(i * i for i in range(1, 100000))


def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-i', '--interval', type=float, default=0.5,
                        help='Collection interval (sec)')
    parser.add_argument('-d', '--duration', type=float, default=1.0,
                        help='Total duration (min)')
    parser.add_argument('-s', '--silent', action='store_true', default=False,
                        help='No stdout')
    parser.add_argument('-e', '--estimated_cpu_percent', type=float,
                        default=3.0, help='Estimated CPU percent')
    args = parser.parse_args()
    pprint(args.__dict__)
    collector = Collector(**args.__dict__)
    collector.start()


if __name__ == '__main__':
    main()
