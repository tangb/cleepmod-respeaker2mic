import unittest
import logging
import sys
sys.path.append('../')
from backend.respeaker2mic import Respeaker2mic
from raspiot.utils import InvalidParameter, MissingParameter, CommandError, Unauthorized
from raspiot.libs.tests import session
import os
import time
from mock import Mock

class TestRespeaker2mic(unittest.TestCase):

    def setUp(self):
        self.session = session.Session(logging.CRITICAL)
        _respeaker2mix = Respeaker2mic
        self.module = self.session.setup(_respeaker2mix)

    def tearDown(self):
        self.session.clean()

if __name__ == "__main__":
    unittest.main()
    
