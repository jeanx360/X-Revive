"""Persist stage-only diagnostics asynchronously, without credentials or arguments."""
import json
import os
from pathlib import Path
import queue
import re
import threading
import time


class Writer:
    def __init__(self,root=Path('/userdata')):
        self.root=Path(root);self.records=queue.Queue(maxsize=128)
        threading.Thread(target=self.run,daemon=True).start()

    def record(self,job_id,message,percent):
        if not re.fullmatch('[a-f0-9]{32}',job_id or ''):return
        item=dict(time=time.time(),message=str(message),percent=percent)
        try:self.records.put_nowait((job_id,item))
        except queue.Full:
            # Keep the newest stage when a slow USB cannot keep up.
            try:self.records.get_nowait();self.records.task_done()
            except queue.Empty:pass
            try:self.records.put_nowait((job_id,item))
            except queue.Full:pass

    def append(self,job_id,item):
        fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            for name in ('X-Revive','diagnosticos','operacoes'):
                try:os.mkdir(name,mode=0o700,dir_fd=fd)
                except FileExistsError:pass
                child=os.open(name,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=fd);os.close(fd);fd=child
            log=os.open(job_id+'.jsonl',os.O_WRONLY|os.O_APPEND|os.O_CREAT|os.O_NOFOLLOW,0o600,dir_fd=fd)
            try:
                data=(json.dumps(item,ensure_ascii=False)+'\n').encode();done=0
                while done<len(data):done+=os.write(log,data[done:])
                os.fsync(log)
            finally:os.close(log)
        finally:os.close(fd)

    def run(self):
        while True:
            job_id,item=self.records.get()
            try:self.append(job_id,item)
            except OSError:pass  # a slow/full USB must not block the interface
            finally:self.records.task_done()
