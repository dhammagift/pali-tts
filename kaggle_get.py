"""Download single files from a Kaggle kernel's output by path, without listing the output (a run that left
thousands of files there gets HTTP 429 on any listing, so `kaggle kernels output` fails).
Usage (on f3): uvx --python 3.12 --with kaggle==2.2.4 python kaggle_get.py <kernel-slug> <dest-dir> <path> [<path>...]
"""
import os
import sys

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiDownloadKernelOutputRequest

slug, dest, paths = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(dest, exist_ok=True)
api = KaggleApi()
api.authenticate()
with api.build_kaggle_client() as client:
    for path in paths:
        req = ApiDownloadKernelOutputRequest()
        req.owner_slug, req.kernel_slug, req.file_path = 'dhammagift', slug, path
        resp = client.kernels.kernels_api_client.download_kernel_output(req)
        with open(os.path.join(dest, os.path.basename(path)), 'wb') as f:
            for chunk in resp.iter_content(1 << 20):
                f.write(chunk)
        print('ok', path)
