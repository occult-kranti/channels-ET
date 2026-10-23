#!/usr/bin/env python3
"""Fetch the pinned public CTranslate2 model with official Hub object checksums."""
import concurrent.futures
import hashlib
import json
from pathlib import Path
import urllib.request

HERE = Path(__file__).resolve().parent
CACHE = Path('/workspace/channels-et-asr-cache/tiny-en')


def main():
    metadata = json.loads((HERE / 'upstream-model-metadata.json').read_text())
    CACHE.mkdir(parents=True, exist_ok=True)

    def fetch(item):
        name = item['path']
        destination = CACHE / name
        url = f"https://huggingface.co/{metadata['modelId']}/resolve/{metadata['revision']}/{name}"

        def valid(blob):
            if len(blob) != item['size']:
                return False
            if item['lfs']:
                return hashlib.sha256(blob).hexdigest() == item['lfs']['sha256']
            return hashlib.sha1(b'blob ' + str(len(blob)).encode() + b'\0' + blob).hexdigest() == item['blobId']

        if not destination.exists() or not valid(destination.read_bytes()):
            temporary = destination.with_suffix(destination.suffix + '.part')
            with urllib.request.urlopen(url, timeout=45) as response, temporary.open('wb') as output:
                total = 0
                while chunk := response.read(1024 * 1024):
                    total += len(chunk)
                    if total > 150 * 1024 * 1024:
                        raise ValueError('Model file exceeds the fixed download budget')
                    output.write(chunk)
            if not valid(temporary.read_bytes()):
                raise ValueError('Official object checksum mismatch: ' + name)
            temporary.replace(destination)
        blob = destination.read_bytes()
        return {'path': name, 'bytes': len(blob), 'sha256': hashlib.sha256(blob).hexdigest(),
                'officialObjectVerified': True, 'sourceUrl': url}

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        files = list(pool.map(fetch, [x for x in metadata['files'] if x['path'] != '.gitattributes']))
    result = {'modelId': metadata['modelId'], 'revision': metadata['revision'], 'license': metadata['license'],
              'localCache': str(CACHE), 'files': files, 'trustRemoteCode': False,
              'scope': 'Verified download of public model files; not a transcription result.'}
    (HERE / 'model-manifest.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({'verifiedModelFiles': len(files), 'cache': str(CACHE)}))


if __name__ == '__main__':
    main()
