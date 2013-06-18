import sys
if sys.version_info < (2, 7):
    # Python 2.6 ships an obsolete version of "unittest"
    sys.modules['unittest'] = __import__('unittest2')
