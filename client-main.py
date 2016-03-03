#!/usr/bin/python
__version__ = "1.0"

import traceback
try:
    from yue.client.client import main
    main()
except Exception as e:
    with open("error.log","w") as f:
        f.write("%s\n"%e)
        f.write(traceback.format_exc())
