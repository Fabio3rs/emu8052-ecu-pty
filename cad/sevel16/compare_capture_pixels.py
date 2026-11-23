"""Separate PNG metadata changes from actual pixels in checkpoint reviews."""
import hashlib
import json
from PIL import Image
from config import OUTPUT
from proof_chain import sha


def run(current='SEVEL_Accessories_A5_v002',previous='SEVEL_Accessories_A5_v001'):
    rows = []
    for path in sorted((OUTPUT/'evidence').glob(current+'*.png')):
        prior = path.with_name(path.name.replace(current,previous,1))
        assert prior.is_file()
        with Image.open(path) as source,Image.open(prior) as before:
            a,b = source.convert('RGB'),before.convert('RGB')
            equal = a.size==b.size and a.tobytes()==b.tobytes()
            pixel_sha = hashlib.sha256(a.tobytes()).hexdigest()
        rows.append({'current':str(path.relative_to(OUTPUT)),
            'previous':str(prior.relative_to(OUTPUT)),
            'current_sha256':sha(path),'previous_sha256':sha(prior),
            'current_rgb_sha256':pixel_sha,'identical_rgb_pixels':equal})
    assert len(rows)==32
    report = {'status':'PASS_PIXEL_COMPARISON_ONLY','document':current,
        'images':rows,'identical_images':sum(r['identical_rgb_pixels'] for r in rows),
        'scope':'Pixel identity supports reuse of an earlier visual review; changed images still require inspection'}
    (OUTPUT/f'reports/{current}_pixel_comparison.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'images':len(rows),'identical':report['identical_images']}))
    return report


if __name__=='__main__':
    run()
