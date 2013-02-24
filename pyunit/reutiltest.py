'''
Created on 13.02.2013

@author: hm
'''
import unittest

from reutil.config import Config
from reutil.util import * 

class Test(unittest.TestCase):


    def setUp(self):
        self._temp = '/tmp/' if os.sep == '/' else 'c:\\temp\\'
        pass
    
    def tearDown(self):
        pass
    
    def testMkDir(self):
        subdir = self._temp + "reutil.tst"
        Util.mkDir(subdir)
        self.assertEquals(True, os.path.exists(subdir))
        Util.mkDir(subdir)
        os.rmdir(subdir)
        self.assertEquals(False, os.path.exists(subdir))
        
    def testWriteFile(self):
        name = self._temp + "reutil.tst.txt"
        content = '''Line 1
line2'''

        Util.writeFile(name, content)
        self.assertEquals(content, Util.readFileAsString(name))
        os.unlink(name)
        
    def testConfig(self):
        conf1 = self._temp + "reutil1.conf"
        conf2 = self._temp + "reutil2.conf"
        Util.writeFile(conf1, '''
include "%s"
value.conf1=True
'''         % conf2)
        Util.writeFile(conf2, '''
value.conf2=4711
'''         )
        conf = Config(conf1)
        self.assertEquals(None, conf.get('NotExistingKey'))
        self.assertEquals('True', conf.get('value.conf1'))
        self.assertEquals('4711', conf.get('value.conf2'))
        os.unlink(conf1)
        os.unlink(conf2)
 
    def testExceptionString(self):
        name = Util.getTempDir(None, True) + 'reutiltest.exceptiontest.txt'
        try:
            open(name, "r")
            self.fail('impossible filename found: ' + name)
        except Exception:
            expected = "addInfoString"
            msg = exceptionString(sys.exc_info(), expected)
            self.assertEquals(True, msg != None)
            self.assertEquals(True, msg.endswith(expected))

    def testBasic(self):
        say('This should be exactly one line! ', False)
        say('We expect an error:')
        sayError('this is the expected ', False)
        sayError(' Error')
        

    def testGetTempDir(self):
        base = Util.getTempDir(None, True)
        name = Util.getTempDir('!test!')
        self.assertEquals(True, name.startswith(base))
        self.assertEqual(True, os.path.exists(name))
        os.rmdir(name)
     
    def testGetTempFile(self):
        subdir = 'reutiltest'
        base = Util.getTempDir(subdir, True)
        os.rmdir(base)
        name = Util.getTempFile('test', subdir)
        self.assertTrue(name.startswith(base))
        os.rmdir(base)
        
if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()