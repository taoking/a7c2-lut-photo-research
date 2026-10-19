"""Offline sRGB/D65 comparison. These metrics do not measure camera accuracy."""
import numpy as np

from ._vendor.sonylooks.color import rows, srgb_decode
from ._vendor.sonylooks.native import metrics


def lab_d65(rgb):
    """CIE 1976 Lab, sRGB primaries and D65 reference white (no adaptation)."""
    xyz = srgb_decode(rows(rgb)) @ np.array([
        [.4124564, .3575761, .1804375],
        [.2126729, .7151522, .0721750],
        [.0193339, .1191920, .9503041],
    ]).T
    relative = xyz / [.95047, 1., 1.08883]
    delta = 6 / 29
    f = np.where(relative > delta**3, np.cbrt(relative),
                 relative / (3 * delta**2) + 4 / 29)
    return np.column_stack([116*f[:, 1]-16, 500*(f[:, 0]-f[:, 1]),
                            200*(f[:, 1]-f[:, 2])])


def compare(actual, expected):
    actual, expected = rows(actual), rows(expected)
    if actual.shape != expected.shape or len(actual) == 0:
        raise ValueError('Matching nonempty RGB rows required')
    difference = np.linalg.norm(lab_d65(actual)-lab_d65(expected), axis=1)
    return {**metrics(actual, expected), 'samples': len(actual),
            'delta_e76_mean': float(difference.mean()),
            'delta_e76_p95': float(np.quantile(difference, .95)),
            'delta_e76_max': float(difference.max())}
