from PIL import Image
import glob
import os
import sys

root = sys.argv[1]
files = sorted(glob.glob(os.path.join(root, 'exports', 'png', 'slide-*.png')))
if len(files) != 20:
    raise SystemExit('expected 20 PNGs, found %d' % len(files))
images = []
for path in files:
    image = Image.open(path).convert('RGB')
    if image.size != (1920, 1080):
        raise SystemExit('%s is %s, expected 1920x1080' % (path, image.size))
    images.append(image)
out = os.path.join(root, 'exports', 'VerifiableTutor_stage.pdf')
images[0].save(out, 'PDF', resolution=96.0, save_all=True, append_images=images[1:])
print('wrote %s with %d pages' % (out, len(images)))
