import importlib, traceback
modules = ['agv','cnc','robot','laser','core','web','config']
results = {}
for m in modules:
    try:
        mod = importlib.import_module(m)
        results[m] = ('OK', None)
    except Exception as e:
        results[m] = ('ERROR', traceback.format_exc())

for m,(status,info) in results.items():
    print(f"MODULE: {m} -> {status}")
    if info:
        print(info)
