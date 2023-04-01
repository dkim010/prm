# pylint:disable=unnecessary-lambda-assignment,import-error
from __future__ import annotations

import argparse
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from pprint import pprint
from subprocess import PIPE, Popen

import psutil

if sys.platform == 'win32':
    import win32api
    import win32con
    import win32pdh
    import win32process


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
                 pid: int,
                 interval: float,
                 duration: float,
                 output_path: Path,
                 silent: bool):
        name = f'{name.lower()}'

        def naming(name):
            return name[:-4] if name[-4:].lower() == '.exe' else name
        self.timers: list[threading.Timer] = []
        self.interval: float = interval
        self.duration: float = duration * 60
        self.cpu_window_size: float = 2.0  # unit: sec
        self.output_path: Path = output_path
        self.silent: bool = silent
        # set proc
        if name:
            found_proc = None
            for proc in psutil.process_iter(['pid', 'name']):
                proc_name = naming(proc.name().lower())
                if proc_name == name:
                    found_proc = proc
                    break
            if found_proc is None:
                raise Exception(f'{name} process was not found')
        else:
            found_proc = psutil.Process(pid=pid)
        self.proc: psutil.Process = found_proc
        # set win32
        if sys.platform == 'win32':
            self.win32_cpu_handle = win32api.OpenProcess(
                win32con.PROCESS_ALL_ACCESS, False, self.proc.pid)
            self.win32_times = (
                time.time(),
                win32process.GetProcessTimes(self.win32_cpu_handle))
            win32_mem_path = \
                f'\\Process({naming(self.proc.name())})\\Working Set - Private'
            self.win32_mem_query = win32pdh.OpenQuery()
            self.win32_mem_handle = win32pdh.AddCounter(
                self.win32_mem_query, win32_mem_path)
        else:
            self.win32_cpu_handle = None
            self.win32_times = None
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

    def collect_usage(self):
        # cpu & memory
        if sys.platform == 'win32':
            cpu_percent = self._get_cpu_usage_win32()
            average_cpu_percent = cpu_percent / psutil.cpu_count(logical=True)
            mem_usage = self._get_mem_usage_win32()
        else:
            cpu_percent = self.proc.cpu_percent(interval=self.cpu_window_size)
            average_cpu_percent = cpu_percent / psutil.cpu_count(logical=False)
            mem_usage = self._get_mem_usage_unix()
        # logging
        with self.output_path.open('a') as stream:
            usage = Usage(
                stamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                pid=self.proc.pid,
                name=self.proc.name(),
                cpu_percent=cpu_percent,
                average_cpu_percent=average_cpu_percent,
                mem_usage=mem_usage)
            stream.write(usage.to_str() + '\n')
            self._stdout(usage.to_str(', '))

    def _get_mem_usage_unix(self):
        args = f'top -l 1 -pid {self.proc.pid} -stats mem -o MEM | tail -1'
        with Popen(['bash', '-lc', args], stdout=PIPE) as process:
            p_out, _ = process.communicate()
        return p_out.decode().strip()

    def _get_cpu_usage_win32(self):
        after = (time.time(),
                 win32process.GetProcessTimes(self.win32_cpu_handle))
        before = self.win32_times
        cpu_percent = \
            ((after[1]['KernelTime'] - before[1]['KernelTime'])
             + (after[1]['UserTime'] - before[1]['UserTime'])) \
            / 10000000 / (after[0] - before[0]) * 100
        self.win32_times = after
        return cpu_percent

    def _get_mem_usage_win32(self):
        win32pdh.CollectQueryData(self.win32_mem_query)
        mem_usage = win32pdh.GetFormattedCounterValue(
            self.win32_mem_handle, win32pdh.PDH_FMT_DOUBLE)[1]
        return f'{round(mem_usage / 1024 / 1024, 2)}M'


def main():
    default_output_path = f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument('-n', '--name', type=str, default='',
                        help='Target process name (case insensitive)\n'
                             '* name or pid is required *')
    parser.add_argument('-p', '--pid', type=int, default=0,
                        help='Target process id\n'
                             '* name or pid is required *')
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
    if (not args.name and not args.pid) or (args.name and args.pid):
        parser.error('Just one of `--name` or `--pid` is required')
    pprint(args.__dict__)
    collector = Collector(**args.__dict__)
    collector.start()


if __name__ == '__main__':
    main()
