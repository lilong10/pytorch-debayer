import cv2
import torch
import argparse
import pandas as pd
import timeit

import debayer

def run_pytorch(deb, t, dev, time_upload=False):
    t = t.pin_memory() if time_upload else t.to(dev)

    def run_once():
        x = t.to(dev, non_blocking=True) if time_upload else t
        rgb = deb(x)

    # Warmup
    run_once()
    run_once()
    run_once()

    torch.cuda.synchronize()
    start = torch.cuda.Event(enable_timing=True)
    end = torch.cuda.Event(enable_timing=True)

    start.record()
    N = 100
    for _ in range(N):
        run_once()
    end.record()
    torch.cuda.synchronize()

    return start.elapsed_time(end)/N 

def run_opencv(b, transparent_api=False):
    # see https://www.learnopencv.com/opencv-transparent-api/
    b = cv2.UMat(b) if transparent_api else b
    def run_cv_once():
        x = cv2.cvtColor(b, cv2.COLOR_BAYER_BG2RGB)

    run_cv_once()
    run_cv_once()
    run_cv_once()

    return timeit.timeit(run_cv_once, number=20)/20*1000

def fmt_line(method, devname, elapsed, mode):
    return f'| {method} | {devname} | {elapsed:4.2f} msec | {mode} |'

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dev', default='cuda')
    parser.add_argument('image')
    args = parser.parse_args()

    b = cv2.imread(args.image, cv2.IMREAD_GRAYSCALE)

    t = (
        torch.from_numpy(b)
        .to(torch.float32)    
        .unsqueeze(0)
        .unsqueeze(0)        
    ) / 255.0

    devname = torch.cuda.get_device_name(args.dev)

    print('Method | Device | Elapsed | Mode |')
    print('|:----:|:------:|:-------:|:----:|')
        
    deb = debayer.Debayer2x2().to(args.dev)
    deb = deb.to(args.dev)
    debname = deb.__class__.__name__
    e = run_pytorch(deb, t, args.dev, time_upload=True)
    print(fmt_line(debname, devname, e, 'time_upload=True'))
    e = run_pytorch(deb, t, args.dev, time_upload=False)
    print(fmt_line(debname, devname, e, 'time_upload=False'))

    
    deb = debayer.Debayer3x3().to(args.dev)
    deb = deb.to(args.dev)
    debname = deb.__class__.__name__
    e = run_pytorch(deb, t, args.dev, time_upload=False)
    print(fmt_line(debname, devname, e, 'time_upload=False'))

    e = run_opencv(b, transparent_api=False)
    print(fmt_line(f'OpenCV {cv2.__version__}', 'CPU ??', e, 'transparent_api=False'))
    e = run_opencv(b, transparent_api=True)
    print(fmt_line(f'OpenCV {cv2.__version__}', 'CPU ??', e, 'transparent_api=True'))


if __name__ == '__main__':
    main()