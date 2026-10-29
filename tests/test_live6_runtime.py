import ast
import errno
import hashlib
import json
from pathlib import Path
import socket
import socketserver
import struct
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1];LIB=ROOT/'cartucho/overlay/usr/local/lib/console';sys.path.insert(0,str(LIB))
import runtime_command,virtual_disc,xiso,ui_rpc,safe_live

class LiveRuntimeTests(unittest.TestCase):
    def test_maintenance_boot_does_not_require_an_application_inventory(self):
        tree=ast.parse((LIB/'installer-worker.py').read_text())
        function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dispatch')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);plan={'boot':{'available':True,'kind':'repair'}}
            def inventory(*args):raise ValueError('inventário instalado ausente/inválido')
            env=dict(status={'busy':False},SOURCE={},layout=types.SimpleNamespace(PRIVATE_STATE=root/'installed'),
                     live_disk=types.SimpleNamespace(PRIVATE=root/'live',plan=lambda *args:plan),
                     maintenance_target=lambda req:('/dev/target',{}),
                     engine=types.SimpleNamespace(installed_manifest=inventory),subprocess=safe_live.subprocess,
                     available=lambda:[dict(identity='selected-id',path='/dev/target',available=True)])
            exec(compile(ast.Module(body=[function],type_ignores=[]),'<maintenance>','exec'),env)
            self.assertEqual(env['dispatch'](dict(action='maintenance-info',target='selected-id')),dict(native=True,plan=plan))
            self.assertIs(env['live_pending'],plan)
            with self.assertRaises(ValueError):env['dispatch'](dict(action='maintenance-info',target='swapped-id'))

    def test_relock_protects_disk_before_a_recreated_partition(self):
        rows={'blockdevices':[dict(path='/dev/sdz',type='disk',children=[dict(path='/dev/sdz4',type='part')])]}
        readonly={'/dev/sdz':False,'/dev/sdz4':False}
        def change(args,**kw):readonly[args[-1]]=True
        def output(args,**kw):
            if args[0].endswith('lsblk'):return json.dumps(rows)
            node=args[-1]
            # Kernel reread replaces the child, clearing its individual flag.
            if node=='/dev/sdz4':readonly[node]=False
            return str(int(readonly[node] or readonly['/dev/sdz']))+'\n'
        with patch.object(safe_live.subprocess,'run',side_effect=change),patch.object(safe_live.subprocess,'check_output',side_effect=output):
            self.assertEqual(safe_live.protect('/dev/source'),['/dev/sdz','/dev/sdz4'])

    def test_disappearing_partition_does_not_defeat_parent_guard_and_disk_failure_is_fatal(self):
        rows={'blockdevices':[dict(path='/dev/sdz',type='disk',children=[dict(path='/dev/sdz4',type='part')])]}
        def output(args,**kw):return json.dumps(rows) if args[0].endswith('lsblk') else '1\n'
        def change(args,**kw):
            if args[-1]=='/dev/sdz4':raise safe_live.subprocess.CalledProcessError(1,args)
        with patch.object(safe_live.subprocess,'run',side_effect=change),patch.object(safe_live.subprocess,'check_output',side_effect=output),patch.object(Path,'exists',return_value=False):
            self.assertEqual(safe_live.protect('/dev/source'),['/dev/sdz'])
        with patch.object(safe_live.subprocess,'run',side_effect=OSError('disk failed')),patch.object(safe_live.subprocess,'check_output',side_effect=output),patch.object(Path,'exists',return_value=False):
            with self.assertRaises(OSError):safe_live.protect('/dev/source')

    def test_virtual_disc_matches_mastered_bytes_with_aliases_renames_holes_and_unaligned_reads(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);tree=root/'tree';tree.mkdir();(tree/'sub').mkdir()
            (tree/'sub/ç.txt').write_bytes(bytes(range(256))*400);(tree/'empty').touch()
            binary=root/'boot.xbe';binary.write_bytes(b'XBEHboot');renames={str(tree/'sub/ç.txt'):'changed.txt'};aliases={'default.xbe':binary}
            image=root/'disc.iso';xiso.build(tree,image,aliases,renames);expected=image.read_bytes();virtual=virtual_disc.Image(tree,aliases,renames)
            try:
                self.assertEqual(virtual.bytes,len(expected))
                for at in range(0,len(expected),379):self.assertEqual(virtual.read(at,min(997,len(expected)-at)),expected[at:at+997])
                with self.assertRaises(ValueError):virtual.read(len(expected)-1,2)
                self.assertEqual((tree/'sub/ç.txt').read_bytes(),bytes(range(256))*400)
            finally:virtual.close()

    def test_nbd_reads_and_refuses_writes(self):
        class Fake:
            def read(self,at,size):return b'0123456789'[at:at+size]
        left,right=socket.socketpair();thread=threading.Thread(target=virtual_disc.serve,args=(right,Fake()));thread.start()
        def request(kind,at,n,body=b''):
            left.sendall(struct.pack('>II8sQI',0x25609513,kind,b'12345678',at,n)+body)
            return struct.unpack('>II8s',virtual_disc.exact(left,16))
        try:
            self.assertEqual(request(0,3,4),(0x67446698,0,b'12345678'));self.assertEqual(virtual_disc.exact(left,4),b'3456')
            self.assertEqual(request(1,0,3,b'BAD')[1],errno.EROFS)
            self.assertEqual(request(3,0,0)[1],0)
            left.sendall(struct.pack('>II8sQI',0x25609513,2,b'12345678',0,0));thread.join(1);self.assertFalse(thread.is_alive())
        finally:left.close();right.close()

    def test_slow_control_rpc_does_not_block_status_or_apply_callbacks_from_thread(self):
        release=threading.Event();results=[];main=threading.get_ident()
        def transport(action):
            if action=='slow':release.wait(2)
            return action
        calls=ui_rpc.Calls(transport)
        try:
            begin=time.monotonic();self.assertTrue(calls.submit('control','slow',lambda value:results.append((value,threading.get_ident())),None));self.assertLess(time.monotonic()-begin,.1)
            self.assertFalse(calls.submit('control','duplicate',None,None))
            calls.submit('status','status',lambda value:results.append((value,threading.get_ident())),None)
            for _ in range(50):
                calls.poll()
                if results:break
                time.sleep(.01)
            self.assertEqual(results,[('status',main)])
            release.set()
            for _ in range(50):
                calls.poll()
                if len(results)==2:break
                time.sleep(.01)
            self.assertEqual(results[-1],('slow',main))
        finally:release.set();calls.pool.shutdown()

    def test_setup_process_has_deadline_and_cancel_kills_child(self):
        with self.assertRaises(TimeoutError):runtime_command.run([sys.executable,'-c','import time;time.sleep(5)'],timeout=.1)
        event=threading.Event();event.set()
        with patch.object(runtime_command,'cancel_event',event):
            with self.assertRaises(runtime_command.OperationCancelled):runtime_command.run([sys.executable,'-c','import time;time.sleep(5)'])
        lines=[];runtime_command.run([sys.executable,'-c',"print('XREVIVE_STAGE teste')"],on_line=lines.append)
        self.assertEqual(lines,['XREVIVE_STAGE teste'])

    def test_status_replies_while_control_dispatch_is_waiting(self):
        tree=ast.parse((LIB/'installer-worker.py').read_text());nodes=[n for n in tree.body if isinstance(n,ast.ClassDef) and n.name in ('Handler','Server')]
        entered=threading.Event();release=threading.Event();context=threading.local()
        def dispatch(request):
            if request['action']=='slow':entered.set();release.wait(3)
            return {'action':request['action'],'operation_id':getattr(context,'operation_id',None)}
        env=dict(socketserver=socketserver,json=json,request_context=context,control_mutex=threading.Lock(),dispatch=dispatch)
        exec(compile(ast.Module(body=nodes,type_ignores=[]),'<server>','exec'),env)
        with tempfile.TemporaryDirectory() as tmp:
            sock=Path(tmp)/'socket';server=env['Server'](str(sock),env['Handler']);thread=threading.Thread(target=server.serve_forever);thread.start()
            def call(action):
                with socket.socket(socket.AF_UNIX) as c:
                    c.settimeout(2);c.connect(str(sock));c.sendall((json.dumps({'action':action,'operation_id':action+'-id'})+'\n').encode());return json.loads(c.makefile().readline())
            slow=threading.Thread(target=lambda:call('slow'));slow.start();self.assertTrue(entered.wait(1))
            try:
                start=time.monotonic();result=call('status');self.assertLess(time.monotonic()-start,.5);self.assertEqual(result['data']['operation_id'],'status-id')
            finally:release.set();slow.join();server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()

class BootMapTests(unittest.TestCase):
    def test_gpt_efi_range_requires_valid_crc_and_bounded_entries(self):
        import binascii,uuid,boot_recovery
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'disk.img';p.write_bytes(bytes(1024**2));entry=bytearray(128)
            entry[:16]=uuid.UUID('c12a7328-f81f-11d2-ba4b-00a0c93ec93b').bytes_le
            struct.pack_into('<QQ',entry,32,1000,1100)
            header=bytearray(512);header[:8]=b'EFI PART';struct.pack_into('<II',header,8,0x10000,92)
            struct.pack_into('<QQ',header,24,1,2047);struct.pack_into('<QIII',header,72,2,1,128,binascii.crc32(entry))
            struct.pack_into('<I',header,16,binascii.crc32(header[:92]))
            with p.open('r+b') as out:out.seek(512);out.write(header);out.write(entry)
            # GPT entry array begins at LBA2, not directly after its 92-byte header.
            rows=boot_recovery.pc_regions(p,p.stat().st_size)
            self.assertEqual(rows,[dict(offset=512000,bytes=101*512,efi=True)])
            with p.open('r+b') as out:out.seek(528);out.write(bytes(4))
            self.assertEqual(boot_recovery.pc_regions(p,p.stat().st_size),[])

    def test_existing_efi_is_replaceable_but_fatx_is_not_free_space(self):
        import boot_existing
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'disk.img'
            with p.open('xb') as out:out.truncate(16*1024**3)
            regions=[dict(drive=d,offset=start,bytes=size) for d,(_,start,size) in zip('ecxyz',__import__('standalone').RETAIL)]
            found=dict(installation=None,regions=regions,device={'path':str(p),'bytes':p.stat().st_size},table='PARTINFO',xbox_bytes=10*1024**3)
            source=dict(regions={n:dict(offset=0,bytes=1024**2) for n in ('system','console','cache','utils')},build_id='new',source_sha256='new')
            with patch.object(boot_existing,'native_sector',return_value=bytes(512)),patch('boot_recovery.pc_regions',return_value=[dict(offset=p.stat().st_size-5*1024**2,bytes=1024**2,efi=True)]):
                offer=boot_existing.offer(found,source);self.assertTrue(offer['available']);self.assertEqual(len(offer['replace_ranges']),1)
                found['xbox_bytes']=p.stat().st_size
                denied=boot_existing.offer(found,source);self.assertFalse(denied['available']);self.assertIn('FATX ocupa',denied['message'])

class StageLogTests(unittest.TestCase):
    def test_logs_only_stages_and_refuses_symlink_parent(self):
        import operation_log
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);writer=operation_log.Writer(root);job='a'*32
            writer.record(job,'Conferindo HDD',5);writer.records.join()
            log=root/'X-Revive/diagnosticos/operacoes'/ (job+'.jsonl')
            row=json.loads(log.read_text());self.assertEqual(set(row),{'time','message','percent'})
            self.assertEqual(row['message'],'Conferindo HDD')
            writer.record('../../bad','not accepted',0);self.assertFalse((root/'bad').exists())
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);outside=root/'other';outside.mkdir();(root/'X-Revive').symlink_to(outside,target_is_directory=True)
            writer=operation_log.Writer(root)
            with self.assertRaises(OSError):writer.append('a'*32,dict(message='safe'))
            self.assertEqual(list(outside.iterdir()),[])


class BootSignatureTests(unittest.TestCase):
    def test_clear_gpt_never_touches_a_signature_inside_fatx(self):
        import installer,standalone,os
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'disk.img';size=16*1024**3
            with p.open('xb') as out:out.truncate(size);out.seek(512);out.write(b'EFI PART');out.seek(size-512);out.write(b'EFI PART')
            fd=os.open(p,os.O_RDWR)
            try:
                data=dict(existing_fatx=True,native_regions=[dict(drive='f',offset=8004132864,bytes=size-8004132864)])
                with patch.object(installer,'drive_regions',return_value={'f':(8004132864,size-8004132864)}):
                    installer.clear_old_gpt(fd,size,data)
                self.assertEqual(os.pread(fd,8,512),bytes(8));self.assertEqual(os.pread(fd,8,size-512),b'EFI PART')
            finally:os.close(fd)

    def test_native_disk_with_known_uefi_can_replace_its_mbr_code(self):
        import boot_existing,standalone,os
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'disk.img';size=16*1024**3
            with p.open('xb') as out:out.truncate(size)
            source=dict(regions={n:dict(offset=0,bytes=1024**2) for n in ('system','console','cache','utils')},build_id='new',source_sha256='new')
            data=__import__('installer').make_layout(size,source)
            regions=[dict(drive=d,offset=start,bytes=length) for d,(_,start,length) in zip('ecxyz',standalone.RETAIL)]
            found=dict(regions=regions,device=dict(path=str(p),bytes=size),xbox_bytes=8004132864)
            first=bytearray(512);first[:3]=b'\xeb\x58\x90';first[498]=0xEF
            struct.pack_into('<II',first,502,data['system']['offset']//512,2048);first[510:]=b'\x55\xaa'
            with p.open('r+b') as out:out.write(first)
            result=boot_existing.native_sector(found,data,bytes(first))
            self.assertEqual(result[:16],standalone.PARTINFO);self.assertEqual(result[498],0xEF)
