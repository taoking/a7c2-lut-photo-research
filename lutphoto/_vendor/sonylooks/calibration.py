"""Build a provisional inverse ST rendering from already aligned patch pairs."""
import numpy as np
from .color import rows, srgb_decode, prophoto_to_srgb
from .native import metrics, validate_response


def validate(data, require_inverse=False):
    if data.get("schema") != "a7c2-look-calibration/1" or not data.get("evidence"):
        raise ValueError("Calibration schema and an evidence description are required")
    if data.get("coordinate_model") != "bt601-limited-provisional":
        raise ValueError("Unsupported native coordinate model")
    validate_response(data["response_matrix"])
    if require_inverse:
        axis, curve, matrix = [np.array(data[k],dtype=float) for k in ("inverse_axis","inverse_curve","inverse_matrix")]
        if axis.ndim != 1 or len(axis) < 2 or axis.shape != curve.shape or not np.isfinite([axis,curve]).all():
            raise ValueError("Invalid inverse ST curve")
        if axis[0] != 0 or axis[-1] != 1 or np.any(np.diff(axis) <= 0) or np.any(np.diff(curve) < 0) or np.any((curve < 0)|(curve > 1)):
            raise ValueError("Inverse ST curve must be monotone over 0..1")
        validate_response(matrix)
    return data


def inverse_st(rgb, calibration):
    validate(calibration,True)
    a = rows(rgb)
    linear_srgb = np.stack([np.interp(a[:,i],calibration["inverse_axis"],calibration["inverse_curve"]) for i in range(3)],axis=1)@np.array(calibration["inverse_matrix"]).T
    return linear_srgb@np.linalg.inv(prophoto_to_srgb()).T


def isotonic(values, weights):
    blocks = []
    for i,(v,w) in enumerate(zip(values,weights)):
        blocks.append([i,i,float(v*w),float(w)])
        while len(blocks) > 1 and blocks[-2][2]/blocks[-2][3] > blocks[-1][2]/blocks[-1][3]:
            right, left = blocks.pop(), blocks.pop()
            blocks.append([left[0],right[1],left[2]+right[2],left[3]+right[3]])
    out = np.empty(len(values))
    for lo,hi,total,w in blocks:
        out[lo:hi+1] = total/w
    return out


def fit(st_rgb, linear_prophoto, split, response, evidence):
    source, linear = rows(st_rgb), rows(linear_prophoto)
    split = np.asarray(split)
    if source.shape != linear.shape or split.shape != (len(source),) or not np.isfinite(split).all():
        raise ValueError("Patch arrays and split IDs must have matching lengths")
    if not np.isin(split,[0,1]).all() or min(np.count_nonzero(split == i) for i in (0,1)) < 32:
        raise ValueError("Use split=0 for training and 1 for held-out patches, at least 32 each")
    if np.any((source < 0)|(source > 1)) or np.any((linear < 0)|(linear > 1)):
        raise ValueError("Patch values must be finite normalized 0..1")
    target = linear@prophoto_to_srgb().T
    s,t = source[split == 0], target[split == 0]
    axis = np.linspace(0,1,65)
    curve, matrix = srgb_decode(axis), np.eye(3)
    for _ in range(12):
        x = np.stack([np.interp(s[:,i],axis,curve) for i in range(3)],axis=1)
        design = x[:,:2]-x[:,2:3]
        ridge = max(float(np.sum(design*design))*.03,1e-5)
        for c in range(3):
            ab = np.linalg.solve(design.T@design+np.eye(2)*ridge,design.T@(t[:,c]-x[:,2])+ridge*np.eye(3)[c,:2])
            row = np.array([ab[0],ab[1],1-ab.sum()])
            for other in range(3):
                if other != c:
                    row[other] = np.clip(row[other],-.15,.15)
            row[c] = 1-sum(row[other] for other in range(3) if other != c)
            matrix[c] = row
        validate_response(matrix)
        ideal = t@np.linalg.inv(matrix).T
        bins = np.clip(np.rint(s.ravel()*64).astype(int),0,64)
        sums = np.bincount(bins,weights=np.clip(ideal.ravel(),0,1),minlength=65)+srgb_decode(axis)*3
        counts = np.bincount(bins,minlength=65).astype(float)+3
        sums[0],counts[0],sums[-1],counts[-1] = 0,1e8,1e8,1e8
        curve = isotonic(sums/counts,counts)
    data = {"schema":"a7c2-look-calibration/1","coordinate_model":"bt601-limited-provisional",
            "response_matrix":validate_response(response).tolist(),"inverse_axis":axis.tolist(),"inverse_curve":curve.tolist(),
            "inverse_matrix":matrix.tolist(),"evidence":evidence,"full_camera_characterization":False,
            "limits":["Patch holdout is not independent-scene validation", "RAW development must retain Sony calibration; no donor camera matrices"]}
    prediction = inverse_st(source[split == 1],data)
    data["linear_prophoto_patch_holdout"] = metrics(prediction,linear[split == 1])
    return data
