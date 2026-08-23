#!/usr/bin/env python3
import threading
import time
import random
import math
import queue
from pathlib import Path
from Aloha.src.utils.budget_utls import cpu_load,memory_load

# ============================================================
#  Utility: Dummy CPU + Memory Load
# ============================================================

def cpu_load(duration_ms=40):
    end = time.time() + (duration_ms / 1000.0)
    x = 0.0
    while time.time() < end:
        x += math.sin(random.random())
    return x

def memory_load(size_kb=256):
    return bytearray(size_kb * 1024)


# ============================================================
#  Base Module Class
# ============================================================

class BaseModule(threading.Thread):
    def __init__(self, name, interval=1.0):
        super().__init__(daemon=True)
        self.name = name
        self.interval = interval
        self.running = False
        self.last_output = None

    def run(self):
        self.running = True
        print(f"[{self.name}] started")

        while self.running:
            start = time.time()

            cpu_load(30)
            memory_load(128)

            self.last_output = self.step()

            elapsed = time.time() - start
            sleep_time = max(0.0, self.interval - elapsed)
            time.sleep(sleep_time)

        print(f"[{self.name}] stopped")

    def stop(self):
        self.running = False

    def step(self):
        return None


# ============================================================
#  CAN Bus Receiver Module (from all nodes)
# ============================================================

class CanBusModule(BaseModule):
    def __init__(self, name, interval=0.1):
        super().__init__(name, interval)
        self.rx_queue = queue.Queue(maxsize=100)

    def step(self):
        # Dummy CAN frame representing data from nodes
        frame = {
            "node": random.choice(["core", "asc", "ptf", "radar"]),
            "msg_type": random.choice(["status", "event", "frame", "track"]),
            "payload": f"dummy-payload-{random.randint(1000,9999)}",
            "timestamp": time.time()
        }

        cpu_load(20)
        memory_load(64)

        try:
            self.rx_queue.put_nowait(frame)
        except queue.Full:
            pass

        print(f"[can] rx from {frame['node']} type={frame['msg_type']}")
        return frame

    def get_frame(self):
        try:
            return self.rx_queue.get_nowait()
        except queue.Empty:
            return None


# ============================================================
#  NAS Writer Module
# ============================================================

class NasWriterModule(BaseModule):
    def __init__(self, name, interval=0.2, base_path="/mnt/nas/sky360"):
        super().__init__(name, interval)
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.write_queue = queue.Queue(maxsize=200)

    def push_record(self, record):
        try:
            self.write_queue.put_nowait(record)
        except queue.Full:
            pass

    def step(self):
        record = None
        try:
            record = self.write_queue.get_nowait()
        except queue.Empty:
            return None

        cpu_load(40)
        memory_load(256)

        node = record["node"]
        ts = record["timestamp"]
        msg_type = record["msg_type"]
        payload = record["payload"]

        day_dir = self.base_path / time.strftime("%Y%m%d", time.gmtime(ts))
        node_dir = day_dir / node
        node_dir.mkdir(parents=True, exist_ok=True)

        fname = node_dir / f"{msg_type}_{int(ts*1000)}.log"
        with open(fname, "a") as f:
            f.write(f"{ts},{msg_type},{payload}\n")

        print(f"[nas] wrote {fname}")
        return str(fname)


# ============================================================
#  Orchestrator
# ============================================================

class Orchestrator:
    def __init__(self):
        self.can = CanBusModule("can", interval=0.1)
        self.nas = NasWriterModule("nas-writer", interval=0.2)

        self.modules = [self.can, self.nas]

    def start(self):
        print("[orchestrator] starting modules")
        for m in self.modules:
            m.start()

        threading.Thread(target=self.loop, daemon=True).start()

    def loop(self):
        while True:
            frame = self.can.get_frame()
            if frame:
                self.nas.push_record(frame)
            time.sleep(0.05)

    def stop(self):
        print("[orchestrator] stopping modules")
        for m in self.modules:
            m.stop()
        for m in self.modules:
            m.join()

    def run(self):
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[orchestrator] shutdown requested")
            self.stop()


# ============================================================
#  Main
# ============================================================

if __name__ == "__main__":
    orch = Orchestrator()
    orch.run()
