import math
import struct
import unittest
from bmd10 import BmdError, Reader, parse_bytes, local_matrix, transform, multiply, obj_text


def fixture():
    chunks = [b'BMD\x0a', b'test.smd'.ljust(32,b'\0'), struct.pack('<HHH',1,1,1), struct.pack('<hhhhh',3,3,3,1,0)]
    for xyz in [(0,0,0),(1,0,0),(0,1,0)]: chunks.append(struct.pack('<hhfff',0,0,*xyz))
    for i in range(3): chunks.append(struct.pack('<hhfffhh',0,0,0,0,1,i,0))
    for uv in [(0,0),(1,0),(0,1)]: chunks.append(struct.pack('<ff',*uv))
    face=bytearray(64);face[0]=3
    for offset in (2,10,18):struct.pack_into('<4h',face,offset,0,1,2,-1)
    chunks += [bytes(face),b'test.jpg'.ljust(32,b'\0'),struct.pack('<hB',1,0),b'\0',b'root'.ljust(32,b'\0'),struct.pack('<h',-1),struct.pack('<6f',1,2,3,0,0,0)]
    return b''.join(chunks)


class BmdTests(unittest.TestCase):
    def test_full_geometry_and_recorded_pose(self):
        model=parse_bytes(fixture())
        self.assertEqual(model['parsed_bytes'],len(fixture()))
        self.assertEqual(len(model['meshes'][0]['vertices']),3)
        self.assertEqual(model['bones'][0]['tracks'][0]['positions'],[[1,2,3]])
        self.assertIn('v 1 2 3\n',obj_text(model))
        self.assertIn('f 1/1/1 2/2/2 3/3/3\n',obj_text(model))

    def test_truncation_at_each_byte_rejected(self):
        raw=fixture()
        for i in range(len(raw)):
            with self.subTest(size=i),self.assertRaises(BmdError):parse_bytes(raw[:i])

    def test_unparsed_trailer_rejected(self):
        with self.assertRaises(BmdError):parse_bytes(fixture()+b'unknown')

    def test_encrypted_versions_rejected(self):
        for version in (12,14,15):
            with self.subTest(version=version),self.assertRaises(BmdError):parse_bytes(fixture()[:3]+bytes([version])+fixture()[4:])

    def test_negative_count_rejected(self):
        raw=bytearray(fixture());struct.pack_into('<h',raw,42,-1)
        with self.assertRaises(BmdError):parse_bytes(raw)

    def test_nonfinite_vertex_rejected(self):
        raw=bytearray(fixture());struct.pack_into('<f',raw,56,math.nan)
        with self.assertRaises(BmdError):parse_bytes(raw)

    def test_active_face_index_rejected_but_unused_preserved(self):
        raw=bytearray(fixture());face_offset=52+48+60+24
        struct.pack_into('<h',raw,face_offset+2,99)
        with self.assertRaises(BmdError):parse_bytes(raw)
        model=parse_bytes(fixture())
        self.assertEqual(model['meshes'][0]['polygons'][0]['vertices'][3],-1)

    def test_unknown_bone_rejected(self):
        raw=bytearray(fixture());struct.pack_into('<h',raw,52,99)
        with self.assertRaises(BmdError):parse_bytes(raw)

    def test_hierarchy_cycle_rejected(self):
        raw=bytearray(fixture());struct.pack_into('<h',raw,len(raw)-26,0)
        with self.assertRaises(BmdError):parse_bytes(raw)

    def test_nonboolean_flag_rejected(self):
        raw=bytearray(fixture());raw[-60]=2
        with self.assertRaises(BmdError):parse_bytes(raw)

    def test_rotation_and_parent_translation(self):
        rot=local_matrix([0,0,0],[0,0,math.pi/2])
        pos=transform(rot,[1,0,0],True)
        self.assertAlmostEqual(pos[0],0);self.assertAlmostEqual(pos[1],1)
        parent=local_matrix([10,20,30],[0,0,0])
        child=local_matrix([1,2,3],[0,0,0])
        self.assertEqual(transform(multiply(parent,child),[0,0,0],True),[11,22,33])
        self.assertEqual(transform(parent,[0,0,1],False),[0,0,1])

    def test_missing_pose_not_invented(self):
        model=parse_bytes(fixture())
        with self.assertRaises(BmdError):obj_text(model,action=1)
        with self.assertRaises(BmdError):obj_text(model,frame=1)

    def test_nonfinite_diagnostic_locates_scalar_after_mixed_fields(self):
        reader = Reader(b'x'+struct.pack('<hhfff',0,0,1,math.inf,3))
        reader.take(1)
        with self.assertRaisesRegex(BmdError, r'Non-finite numeric data.*layout offset 9$'):
            reader.unpack('hhfff')

    def test_active_normal_diagnostic_locates_corner_and_value(self):
        raw = bytearray(fixture())
        struct.pack_into('<h',raw,198,3)
        with self.assertRaisesRegex(BmdError, r'polygon 0: invalid active normal index 3 at corner 2.*layout offset 198$'):
            parse_bytes(raw)

    def test_negative_vertex_bone_diagnostic_locates_record(self):
        raw = bytearray(fixture())
        struct.pack_into('<h',raw,68,-8888)
        with self.assertRaisesRegex(BmdError, r'vertex 1: unsupported vertex bone -8888.*layout offset 68$'):
            parse_bytes(raw)

    def test_negative_normal_bone_diagnostic_locates_record(self):
        raw = bytearray(fixture())
        struct.pack_into('<h',raw,140,-1)
        with self.assertRaisesRegex(BmdError, r'normal 2: unsupported normal bone -1.*layout offset 140$'):
            parse_bytes(raw)

    def test_dummy_parent_diagnostic_locates_actual_parent_edge(self):
        raw = bytearray(fixture())
        struct.pack_into('<H',raw,38,3)
        bone0 = len(raw)-59
        struct.pack_into('<h',raw,bone0+33,1)
        raw += b'\0'+b'child'.ljust(32,b'\0')+struct.pack('<h6f',2,0,0,0,0,0,0)+b'\1'
        with self.assertRaisesRegex(BmdError, r'Bone 1: parent 2 references dummy bone.*layout offset 375$'):
            parse_bytes(raw)

if __name__=='__main__':unittest.main()
