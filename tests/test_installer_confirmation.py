"""Exercise the real GUI hold/release state without importing SDL on the host."""
import ast
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
source=ast.parse((ROOT/'cartucho/overlay/usr/local/lib/console/installer-ui.py').read_text())
node=next(n for n in source.body if isinstance(n,ast.ClassDef) and n.name=='Confirmation')
scope={};exec(compile(ast.Module(body=[node],type_ignores=[]),'confirmation','exec'),scope)
Confirmation=scope['Confirmation']


class ConfirmationTest(unittest.TestCase):
    def test_held_before_dialog_and_held_across_dialogs_never_double_confirm(self):
        c=Confirmation()
        self.assertFalse(c.update(True,0))
        self.assertFalse(c.update(True,10))
        self.assertFalse(c.update(False,11))
        self.assertFalse(c.update(True,12))
        self.assertTrue(c.update(True,14))
        self.assertFalse(c.update(True,20))
        self.assertFalse(c.update(False,21))
        self.assertFalse(c.update(True,22))
        self.assertTrue(c.update(True,24))

    def test_taps_do_not_accumulate_hold_time(self):
        c=Confirmation();c.update(False,0)
        for now in range(1,20):
            self.assertFalse(c.update(True,now))
            self.assertFalse(c.update(False,now+.1))


if __name__=='__main__':unittest.main()
