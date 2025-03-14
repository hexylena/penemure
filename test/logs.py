import unittest
import jsondiff
from penemure.logs import *

EXAMPLE = {
    'a': 'b',
    1: 2,
    'list': [1, 2, 3],
    'dict': {
        'a': 'b',
        1: 2,
        'list': [1, 2, 3],
    },
    'ld': [
        {'a': 'b'},
        {1: 2},
    ]
}

class TestUnSafeFunction(unittest.TestCase):
    def test_safe(self):
        o = {
            'a': 'b',
            1: 2, 
            'list': {'xMpCOKC5': 1, 'yB5yjZ1M': 2, '7MvIfktc': 3, '__order': 'xMpCOKC5|yB5yjZ1M|7MvIfktc'},
            'dict': {
                'a': 'b',
                1: 2,
                'list': {'xMpCOKC5': 1, 'yB5yjZ1M': 2, '7MvIfktc': 3, '__order': 'xMpCOKC5|yB5yjZ1M|7MvIfktc'}
            }, 
            'ld': {
                'vXIrlqC/': {'a': 'b'},
                'llX/LSqO': {1: 2},
                '__order': 'vXIrlqC/|llX/LSqO'
            }
        }
        self.assertEqual({}, jsondiff.diff(safe(EXAMPLE), {'root': o}))

    def test_roundtrip(self):
        self.assertEqual({}, jsondiff.diff(
            EXAMPLE,
            unsafe(safe(EXAMPLE))
        ))
        self.assertEqual({}, jsondiff.diff(
            EXAMPLE,
            unsafe(safe(unsafe(safe(EXAMPLE))))
        ))


if __name__ == '__main__':
    unittest.main()
