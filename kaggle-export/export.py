"""Kaggle CPU job: export ONNX from checkpoints of the pali-voice-train run (dataset pali-voice-ckpt).

That run trained fine but died in its export step: torch's new dynamo exporter fails on VITS
(data-dependent assert in rational_quadratic_spline), so the legacy exporter is forced here.
Exports the last checkpoint, the best by validation (epoch 299) and an early one, for a blind listening test.
"""
import glob
import os
import subprocess

W = '/kaggle/working'
ckpts = sorted(glob.glob('/kaggle/input/**/*.ckpt', recursive=True))
config = glob.glob('/kaggle/input/**/pali_dg-medium.onnx.json', recursive=True)[0]
print('\n'.join(ckpts), config, flush=True)


def sh(cmd):
    print('+', cmd, flush=True)
    r = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    print(r.stdout[-8000:], flush=True)
    if r.returncode:
        open(f'{W}/error.txt', 'a').write(f'$ {cmd}\n\n{r.stdout[-8000:]}\n')
    return r.returncode


sh(f'git clone -q --depth 1 https://github.com/OHF-Voice/piper1-gpl.git {W}/piper1-gpl')
os.chdir(f'{W}/piper1-gpl')
# legacy TorchScript exporter: torch >= 2.9 defaults to dynamo, which cannot trace VITS
sh("sed -i 's/torch.onnx.export(/torch.onnx.export(dynamo=False, /' src/piper/train/export_onnx.py")
sh("pip install -q cython scikit-build 'cmake<4' ninja onnx -e '.[train]'")
sh('bash build_monotonic_align.sh && python setup.py build_ext --inplace -q')
os.makedirs(f'{W}/out', exist_ok=True)
sh(f'cp {config} {W}/out/')
for c in ckpts:
    name = os.path.basename(c)[:-5]
    sh(f'python -m piper.train.export_onnx --checkpoint "{c}" --output-file {W}/out/pali_dg-{name}.onnx')
sh(f'rm -rf {W}/piper1-gpl')
sh(f'ls -la {W}/out')
