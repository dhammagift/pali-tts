"""Rebuild a trainable checkpoint of a Piper voice that is published only as ONNX (pratham), so it can be fine-tuned
itself, keeping its timbre and quality (owner, 2026-10-10: «переучить читать, но оставить тембр и качество»).
rohan's checkpoint (the same medium architecture) gives the parts the inference ONNX lacks: the posterior encoder,
the duration predictor's training flows, the discriminator. pratham's ONNX gives the whole generator: most weights
keep their names; weight-normed convs are folded (some with anonymous names) and are found by the node that uses
them (/dec/ups.0/ConvTranspose -> dec.ups.0), stored back as weight_v = W, weight_g = |W|.
Check: the rebuilt generator and the ONNX, same input, no noise -> the same audio.
Usage (piper[train] installed): python rebuild_pratham_ckpt.py models/hi_IN-pratham-medium.onnx rohan.ckpt pratham.ckpt
"""
import sys

import numpy as np
import onnx
import onnxruntime as ort
import torch
from onnx import numpy_helper
from piper.train.vits.lightning import VitsModel

ONNX, ROHAN, OUT = sys.argv[1:4]
g = VitsModel.load_from_checkpoint(ROHAN, map_location='cpu', weights_only=False).model_g
sd = g.state_dict()
m = onnx.load(ONNX)
inits = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
users = {}
for n in m.graph.node:
    for idx, inp in enumerate(n.input):
        if inp in inits:
            users.setdefault(inp, []).append((n.name, n.op_type, idx))
done, skipped = set(), []


def put(key, arr):
    t = torch.as_tensor(np.array(arr)).to(sd[key].dtype)
    assert tuple(t.shape) == tuple(sd[key].shape), (key, t.shape, sd[key].shape)
    sd[key].copy_(t)
    done.add(key)


for name, arr in inits.items():
    if name in sd and tuple(sd[name].shape) == arr.shape:
        put(name, arr)
        continue
    us = users.get(name, [])
    if not us:
        skipped.append((name, arr.shape, 'unused'))
        continue
    node, op, idx = us[0]
    path = '.'.join(node.strip('/').split('/')[:-1])
    if op in ('Conv', 'ConvTranspose'):
        param = {1: 'weight', 2: 'bias'}.get(idx)
    elif op == 'Gather' and idx == 0:
        param = 'weight'
    elif op == 'Exp':  # ElementwiseAffine keeps logs and exports exp(logs)
        param = 'logs'
    else:
        param = None
    key = f'{path}.{param}'
    if param == 'logs':
        arr = -arr  # reverse flow: x * exp(-logs), the Neg folded into the constant
    if param and key in sd and tuple(sd[key].shape) == arr.shape:
        put(key, arr)
    elif param == 'weight' and f'{path}.weight_v' in sd:
        w = torch.as_tensor(np.array(arr))
        gshape = sd[f'{path}.weight_g'].shape
        put(f'{path}.weight_v', w)
        put(f'{path}.weight_g', w.norm(dim=[d for d in range(w.dim()) if gshape[d] == 1], keepdim=True))
    else:
        skipped.append((name, arr.shape, node, op, idx))
# dp.flows.1 is the SDP flow VITS drops at inference ("a useless vflow"): not in the ONNX, kept from rohan for training
infer_keys = [k for k in sd if not k.startswith(('enc_q.', 'dp.post_', 'dp.flows.1.'))]
missing = [k for k in infer_keys if k not in done]
print('filled', len(done), 'of', len(sd), '| ONNX weights not placed:', len(skipped))
for s in skipped[:12]:
    print('  not placed', s)
print('inference weights still rohan\'s:', len(missing), missing[:15])
g.load_state_dict(sd)
g.eval()  # dropout off for the check
ids = torch.LongTensor([[1, 0, 31, 0, 120, 0, 27, 0, 14, 0, 26, 0, 120, 0, 3, 0, 23, 0, 27, 0, 2]])
with torch.no_grad():
    a = g.infer(ids, torch.LongTensor([ids.shape[1]]), noise_scale=0.0, length_scale=1.0, noise_scale_w=0.0)[0]
a = a.reshape(-1).numpy()
b = ort.InferenceSession(ONNX).run(None, {'input': ids.numpy(), 'input_lengths': np.array([ids.shape[1]]),
                                          'scales': np.array([0.0, 1.0, 0.0], dtype=np.float32)})[0].reshape(-1)
n = min(len(a), len(b))
print('samples', len(a), len(b), '| correlation', round(float(np.corrcoef(a[:n], b[:n])[0, 1]), 5),
      '| max abs diff', round(float(np.abs(a[:n] - b[:n]).max()), 5))
ck = torch.load(ROHAN, map_location='cpu', weights_only=False)
for k, v in g.state_dict().items():
    ck['state_dict']['model_g.' + k] = v
ck['epoch'], ck['global_step'] = 0, 0
torch.save(ck, OUT)
print('saved', OUT)
