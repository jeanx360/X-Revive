"""Background RPC transport; callbacks run only in the UI's poll loop."""
import concurrent.futures
import queue


class Calls:
    def __init__(self,transport):
        self.transport=transport;self.pool=concurrent.futures.ThreadPoolExecutor(max_workers=2)
        self.pending=set();self.results=queue.SimpleQueue()

    def submit(self,channel,action,success,failure,**args):
        if channel in self.pending:return False
        self.pending.add(channel)
        def perform():
            try:self.results.put((channel,success,self.transport(action,**args)))
            except Exception as exc:self.results.put((channel,failure,exc))
        self.pool.submit(perform);return True

    def poll(self):
        while not self.results.empty():
            channel,callback,value=self.results.get();self.pending.remove(channel)
            if callback:callback(value)
