"""Explicit color spaces; no camera calibration is bundled."""
import numpy as np


def rows(values):
    a = np.asarray(values, dtype=float)
    if a.ndim != 2 or a.shape[1] != 3 or not np.isfinite(a).all():
        raise ValueError("Expected finite Nx3 RGB rows")
    return a


def srgb_encode(x):
    x = np.maximum(x, 0)
    return np.where(x <= .0031308, 12.92*x, 1.055*x**(1/2.4)-.055)


def srgb_decode(x):
    x = np.maximum(x, 0)
    return np.where(x <= .04045, x/12.92, ((x+.055)/1.055)**2.4)


def rgb_xyz(primaries, white):
    def xyz(xy):
        x, y = xy
        return np.array([x/y, 1, (1-x-y)/y])
    m = np.column_stack([xyz(p) for p in primaries])
    return m*np.linalg.solve(m, xyz(white))[None, :]


def prophoto_to_srgb():
    bradford = np.array([[.8951,.2664,-.1614],[-.7502,1.7135,.0367],[.0389,-.0685,1.0296]])
    d50 = np.array([.3457/.3585, 1, (1-.3457-.3585)/.3585])
    d65 = np.array([.3127/.3290, 1, (1-.3127-.3290)/.3290])
    adapt = np.linalg.inv(bradford)@np.diag((bradford@d65)/(bradford@d50))@bradford
    pro = rgb_xyz([(.7347,.2653),(.1596,.8404),(.0366,.0001)], (.3457,.3585))
    srgb = rgb_xyz([(.64,.33),(.30,.60),(.15,.06)], (.3127,.3290))
    return np.linalg.inv(srgb)@adapt@pro


def rgb_to_hsv(rgb):
    a = rows(rgb)
    hi, lo = a.max(1), a.min(1)
    d = hi-lo
    hue = np.zeros(len(a))
    idx = a.argmax(1)
    for channel, numerator, offset in [(0,a[:,1]-a[:,2],0), (1,a[:,2]-a[:,0],2), (2,a[:,0]-a[:,1],4)]:
        mask = (idx == channel) & (d > 1e-14)
        hue[mask] = numerator[mask]/d[mask]+offset
    saturation = np.divide(d, hi, out=np.zeros_like(d), where=hi > 1e-14)
    return np.column_stack([(hue*60)%360, saturation, hi])


def hsv_to_rgb(hsv):
    h, s, v = rows(hsv).T
    h = (h%360)/60
    sector = np.floor(h).astype(int)
    f = h-sector
    p, q, t = v*(1-s), v*(1-s*f), v*(1-s*(1-f))
    choices = np.stack([np.column_stack(x) for x in [(v,t,p),(q,v,p),(p,v,t),(p,q,v),(t,p,v),(v,p,q)]])
    return choices[sector, np.arange(len(h))]
