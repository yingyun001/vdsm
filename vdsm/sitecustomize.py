import sys
from vdsm.config import config

if sys.version_info[0] == 2:
    # Allow mixing of unicode objects and strings encoded in utf8.
    sys.setdefaultencoding('utf8')

if config.getboolean('devel', 'coverage_enable'):
    import coverage
    coverage.process_startup()
