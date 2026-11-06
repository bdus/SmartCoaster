#!/usr/bin/env python3
"""Orientation-baking helpers for the 3D-print delivery stage (task-6).

Physics: the Kromacut print's artwork face must be the FIRST layer on the build
plate, so the plate+print unit is printed TOP-FACE-DOWN: the plate's original top
face (rim) lies on the bed, the recess opens downward and the print (art face
down) is nested inside it.  After printing the finished part is flipped over.

All transforms are rigid (rotation + translation), so triangle counts and
volumes are preserved; only the orientation/position changes.

Row-vector convention: v' = v @ R.T + t   (mm).
"""
import hashlib
import struct

import numpy as np

ID = np.eye(3)
RX180 = np.array([[1.0, 0.0, 0.0],
                  [0.0, -1.0, 0.0],
                  [0.0, 0.0, -1.0]])
RZ90 = np.array([[0.0, -1.0, 0.0],
                 [1.0, 0.0, 0.0],
                 [0.0, 0.0, 1.0]])
# +90 deg about X: thickness axis Y -> +Z (button lies flat like a coin); the
# native -Y visible/cap face points to -Z, i.e. DOWN on the bed.
RX90 = np.array([[1.0, 0.0, 0.0],
                 [0.0, 0.0, -1.0],
                 [0.0, 1.0, 0.0]])


def read_stl(path):
    """Read a binary STL -> (n,3,3) float64 triangle array in mm."""
    with open(path, "rb") as fh:
        head = fh.read(84)
        if len(head) < 84:
            raise ValueError("STL too short: " + path)
        n = struct.unpack("<I", head[80:84])[0]
        raw = fh.read(n * 50)
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(n, 50)
    return arr[:, 12:48].copy().view("<f4").reshape(n, 3, 3).astype(np.float64)


def write_stl(path, tris, header=b"SmartCoaster print-delivery"):
    """Write a binary STL from (n,3,3) triangles; recompute facet normals."""
    tris = np.asarray(tris, dtype=np.float64)
    e1 = tris[:, 1] - tris[:, 0]
    e2 = tris[:, 2] - tris[:, 0]
    nrm = np.cross(e1, e2)
    ln = np.linalg.norm(nrm, axis=1, keepdims=True)
    nrm = np.divide(nrm, ln, out=np.zeros_like(nrm), where=ln > 1e-12)
    rec = np.zeros((len(tris), 12), dtype="<f4")
    rec[:, 0:3] = nrm
    rec[:, 3:6] = tris[:, 0]
    rec[:, 6:9] = tris[:, 1]
    rec[:, 9:12] = tris[:, 2]
    buf = bytearray(header[:80].ljust(80, b" "))
    buf += struct.pack("<I", len(tris))
    for i in range(len(tris)):
        buf += rec[i].tobytes() + b"\x00\x00"
    with open(path, "wb") as fh:
        fh.write(buf)


def tri_bbox(tris):
    v = np.asarray(tris).reshape(-1, 3)
    return v.min(0), v.max(0)


def rot_bbox(R, lo, hi):
    lo = np.asarray(lo, dtype=float)
    hi = np.asarray(hi, dtype=float)
    corners = np.array([[x, y, z] for x in (lo[0], hi[0])
                        for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
    v = corners @ np.asarray(R).T
    return v.min(0), v.max(0)


def bake_matrix(R, lo, hi):
    """4x4 row-vector matrix: rotate by R, centre XY on 0, put min Z on 0 (mm)."""
    lo2, hi2 = rot_bbox(R, lo, hi)
    t = np.array([-(lo2[0] + hi2[0]) / 2.0,
                  -(lo2[1] + hi2[1]) / 2.0,
                  -lo2[2]])
    M = np.eye(4)
    M[:3, :3] = np.asarray(R, dtype=float)
    M[3, :3] = t
    return M


def apply_matrix(M, tris):
    v = np.asarray(tris, dtype=np.float64).reshape(-1, 3)
    return (v @ M[:3, :3].T + M[3, :3]).reshape(-1, 3, 3)


def volume_mm3(tris):
    """Signed volume of a closed triangle mesh (mm^3), absolute value."""
    t = np.asarray(tris, dtype=np.float64)
    v0, v1, v2 = t[:, 0], t[:, 1], t[:, 2]
    return abs(float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0))


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def mat_lists(M):
    return {"R": [[float(x) for x in row] for row in M[:3, :3]],
            "t": [float(x) for x in M[3, :3]]}
