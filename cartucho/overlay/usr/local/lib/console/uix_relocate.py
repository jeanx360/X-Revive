"""Relocate the locked UIX Lite resource volume without changing stock C:."""
import hashlib
import re

ORIGINAL_SHA256='d9c0e54b12a5bf92f250d7c0f7d5c2d0d2334832935b7b9e7e6acb384dd5c18d'
EXPECTED_OFFSETS=(64348,64684,65548,65648,1389108,1447912,1454448,1503408,1503444)


def relocate(data):
    if hashlib.sha256(data).hexdigest()!=ORIGINAL_SHA256:
        raise ValueError('UIX Lite mudou; revisar relocação antes de compilar')
    matches=list(re.finditer(rb'\\Device\\Harddisk0\\Partition2(?=\\|\x00)',data,re.I))
    if tuple(m.start() for m in matches)!=EXPECTED_OFFSETS:
        raise ValueError('referências UIX Lite inesperadas')
    result=bytearray(data)
    for match in matches:result[match.end()-1]=ord('6')
    return bytes(result)
