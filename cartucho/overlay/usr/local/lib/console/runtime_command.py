"""Bounded appliance setup commands with streamed diagnostics, never passwords."""
import os
import selectors
import signal
import subprocess
import time

cancel_event=None


class OperationCancelled(Exception):pass


def run(args, *, timeout=30, env=None, on_line=None):
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                             env=env,start_new_session=True)
    selector=selectors.DefaultSelector();selector.register(process.stdout,selectors.EVENT_READ)
    deadline=time.monotonic()+timeout;pending=b'';lines=[]
    try:
        while selector.get_map():
            if cancel_event is not None and cancel_event.is_set():raise OperationCancelled('Operação cancelada')
            if time.monotonic()>deadline:
                raise TimeoutError(f'A etapa {os.path.basename(str(args[0]))} não respondeu em {timeout}s. Consulte os detalhes e tente novamente.')
            for key,_ in selector.select(.2):
                block=os.read(key.fileobj.fileno(),65536)
                if not block:selector.unregister(key.fileobj);continue
                pending+=block
                while b'\n' in pending:
                    line,pending=pending.split(b'\n',1);line=line.decode(errors='replace')
                    lines.append(line);lines=lines[-30:];print(line,flush=True)
                    if on_line:on_line(line)
        if pending:
            line=pending.decode(errors='replace');lines.append(line);print(line,flush=True)
            if on_line:on_line(line)
        code=process.wait(timeout=max(.1,deadline-time.monotonic()))
        if code:raise ValueError(f'{os.path.basename(str(args[0]))} falhou ({code}): '+ '\n'.join(lines[-3:]))
        return '\n'.join(lines)
    finally:
        selector.close();process.stdout.close()
        if process.poll() is None:
            os.killpg(process.pid,signal.SIGKILL);process.wait()
