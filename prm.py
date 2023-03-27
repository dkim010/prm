from __future__ import annotations

import argparse
from subprocess import Popen, PIPE
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pprint import pprint

import psutil


@dataclass
class Usage:
    stamp: str
    pid: int
    name: str
    cpu_percent: float
    average_cpu_percent: float
    mem_usage: str

    def to_str(self, delim: str = ','):
        return delim.join(str(elem) for elem in [
            self.stamp,
            self.pid,
            self.name,
            round(self.cpu_percent, 2),
            round(self.average_cpu_percent, 2),
            self.mem_usage,
        ])


class Collector:
    def __init__(self,
                 name: str,
                 interval: float,
                 duration: float,
                 output_path: Path,
                 silent: bool):
        self.name: str = f'{name.lower()}'
        if sys.platform == 'win32':
            self.name += '.exe'
        self.timers: list[threading.Timer] = []
        self.interval: float = interval
        self.duration: float = duration * 60
        self.cpu_window_size: float = 2.0  # unit: sec
        self.output_path: Path = output_path
        self.silent: bool = silent
        self.proc: psutil.Process = None
        # create (overwrite)
        with self.output_path.open('w') as stream:
            # pylint:disable=no-member
            stream.write(','.join(Usage.__dataclass_fields__.keys()) + '\n')
            self._stdout(', '.join(Usage.__dataclass_fields__.keys()))

    def _stdout(self, *lines: str):
        if not self.silent:
            print(*lines)

    def start(self):
        try:
            self.proc = self._get_proc(self.name)
            start_time = time.time()
            for i in range(int(self.duration / self.interval + 1)):
                # cleanup
                for j in range(len(self.timers) - 1, -1, -1):
                    if not self.timers[j].is_alive():
                        self.timers.pop(j)
                # add new timer
                timer = threading.Timer(0.0, self.collect_usage)
                timer.start()
                self.timers.append(timer)
                # sleep remained time
                time.sleep((start_time + (i + 1) * self.interval) - time.time())
        finally:
            # cancel all timers
            for timer in self.timers:
                timer.cancel()

    @classmethod
    def _get_proc(cls, name):
        found_proc = None
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.name().lower() == name:
                found_proc = proc
                break
        if found_proc is None:
            raise Exception(f'{name} process was not found')
        return found_proc

    def collect_usage(self):
        cpu_percent = self.proc.cpu_percent(interval=self.cpu_window_size)
        average_cpu_percent = cpu_percent / psutil.cpu_count(logical=False)
        if sys.platform == 'win32':
            mem_usage = self._get_mem_usage_windows()
        else:
            mem_usage = self._get_mem_usage_unix()
        with self.output_path.open('a') as stream:
            usage = Usage(
                stamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                pid=self.proc.pid,
                name=self.proc.name(),
                cpu_percent=cpu_percent,
                average_cpu_percent=average_cpu_percent,
                mem_usage=mem_usage)
            stream.write(usage.to_str()+ '\n')
            self._stdout(usage.to_str(', '))

    def _get_mem_usage_unix(self):
        args = f'top -l 1 -pid {self.proc.pid} -stats mem -o MEM | tail -1'
        with Popen(['bash', '-lc', args], stdout=PIPE) as process:
            p_out, _ = process.communicate()
        return p_out.decode().strip()

    def _get_mem_usage_windows(self):
        # pylint:disable=anomalous-backslash-in-string
        cmd = '(Get-Counter -Counter ' \
            '"\Process(' \
            f'$((Get-Process -Id {self.proc.pid}).Name)' \
            ')\Working Set - Private"' \
            ').CounterSamples.CookedValue'
        with Popen(['powershell.exe', cmd], stdout=PIPE) as process:
            p_out, _ = process.communicate()
        return f'{int(p_out) / 1024 / 1024}M'


def main():
    default_output_path = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-n', '--name', type=str, required=True,
                        help='Target process name (case insensitive)')
    parser.add_argument('-i', '--interval', type=float, default=1.0,
                        help='Collection interval (sec)')
    parser.add_argument('-d', '--duration', type=float, default=1.0,
                        help='Total duration (min)')
    parser.add_argument('-o', '--output_path', type=Path,
                        default=Path(default_output_path),
                        help='The output CSV file path')
    parser.add_argument('-s', '--silent', action='store_true', default=False,
                        help='No stdout')
    args = parser.parse_args()
    pprint(args.__dict__)
    collector = Collector(**args.__dict__)
    collector.start()


if __name__ == '__main__':
    main()
