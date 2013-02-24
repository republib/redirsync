# Project: https://github.com/republib/republib/wiki
# Licence: Public domain: http://www.wtfpl.net

import unittest, os.path, re, time
from dirsync.redirsync import Sync, main, SearchCriteria
from reutil.util import say
from reutil.config import Config

class Test(unittest.TestCase):
    def setUp(self):
        self._base = base = "/tmp" if os.sep == "/" else "c:\\temp"
        sep = os.sep
        self._configFile = base + sep + "redirsynctest.conf"
        self.mkFile(self._configFile, """
excluded-dirs=^(temp|cache)$
excluded-files=(~|\.(bak|)$
"""
            )
        self._logFile = self._base + sep + "testdirsync.log"

        self._lastNode = "src_dirsync"
        self._src = base + sep + self._lastNode + sep
        self._trg = base + sep + "trg_dirsync" + sep
        self._subdir1 = "dir1" + sep
        self._file1 = "file1.log"
        self._file2 = "file2.txt"
        self._file1_1 = self._subdir1 + "mylog1.log"
        self._file1_2 = self._subdir1 + "mytext2.txt"
        self._srcFile1 = self._src + self._file1;
        self._srcFile2 = self._src + self._file2;
        self._srcFile1_1 = self._src + self._file1_1;
        self._srcFile1_2 = self._src + self._file1_2;
        self._trgFile1 = self._trg + self._file1;
        self._trgFile2 = self._trg + self._file2;
        self._trgFile1_1 = self._trg + self._file1_1;
        self._trgFile1_2 = self._trg + self._file1_2;

        self.populateSrc()
       
        self._args = DummyArgs(["patterns:", "verbose:1", "update:1", "size:1",
            "add:1"])

    def populateSrc(self):
        self.mkDir(self._src)
        self.mkDir(self._src + self._subdir1)
        self.mkDir(self._trg)
        self.mkFile(self._srcFile1)
        self.mkFile(self._srcFile2)
        self.mkFile(self._srcFile1_1)
        self.mkFile(self._srcFile1_2)
        

    def tearDown(self):
        pass
    
    def log(self, msg):
        say(msg)
        
    def mkDir(self, path):
        if not os.path.exists(path):
            os.mkdir(path)
    def mkFile(self, path, content = None):
        if not os.path.exists(path):
            fp = open(path, "w")
            if content == None:
                content = path + "\nLine2" 
            fp.write(content);
            fp.close()
            
    def rmDir(self, path):
        if os.path.exists(path) and os.path.isdir(path):
            os.rmdir(path)
            
    def rmFile(self, path):
        if os.path.exists(path) and os.path.isfile(path):
            os.unlink(path)
        
    def removeTarget(self):
        self.rmFile(self._trg + self._file1_2)
        self.rmFile(self._trg + self._file1_1)
        self.mkDir(self._trg + self._subdir1)
        
        self.rmFile(self._trg + self._file2)
        self.rmFile(self._trg + self._file1)
        
    def testHasWildcard(self):
        criteria = SearchCriteria()
        self.assertEquals(True, criteria.hasWildcards("*.abc"))
        self.assertEquals(True, criteria.hasWildcards("abc*.abc"))
        self.assertEquals(True, criteria.hasWildcards("abc*"))
        self.assertEquals(True, criteria.hasWildcards("?"))
        self.assertEquals(True, criteria.hasWildcards("[ab]"))
        self.assertEquals(True, criteria.hasWildcards("ab]"))
       
        self.assertEquals(False, criteria.hasWildcards("ab.def"))
        
    def testAddPatterns(self):
        criteria = SearchCriteria()
        criteria.addPatterns(["*.txt", "-*.bak", "*pic*", "-*tmp[1-9].txt"])
        self.assertEquals(".txt", criteria._includeEndsWith[0])
        self.assertEquals(".bak", criteria._excludeEndsWith[0])
        self.assertEquals("*pic*", criteria._includePatterns[0])
        self.assertEquals("*tmp[1-9].txt", criteria._excludePatterns[0])
        
       
    def testBasic(self):
        sync = Sync()
        sync.log("log is running")
        sync.error("error is running")
        sync.close()
        
    def testMatches(self):
        criteria = SearchCriteria()
        criteria.addPatterns(["*.txt", "-*.bak", "*pic*", "-*tmp[1-9].txt"])
        self.assertEquals(True, criteria.matches("test.txt"))
        self.assertEquals(False, criteria.matches("test.tmp3.txt"))
        self.assertEquals(True, criteria.matches("mypicture"))
        self.assertEquals(False, criteria.matches("pic.bak"))
                          
        criteria = SearchCriteria()
        criteria.addPatterns(["*", "-*.bak", "-*tmp*", "-*[1-9]*"])
        self.assertEquals(True, criteria.matches("test.txt"))
        self.assertEquals(False, criteria.matches("test.bak"))
        self.assertEquals(False, criteria.matches("test3.txt"))
        self.assertEquals(False, criteria.matches("tmp"))
        self.assertEquals(False, criteria.matches("anytmp"))
        self.assertEquals(False, criteria.matches("anytmp.bak"))
       
    def testDeleteFile(self):
        sync = Sync()
        full = self._base + os.sep + 'todelete.dat'
        self.mkFile(full, '')
        self.assertEquals(True, os.path.exists(full))
        sync.deleteFile(full)
        self.assertEquals(False, os.path.exists(full))
        self.log('Deleting a not existing file: ' + full)
        sync.deleteFile(full)
        sync.close()
        
    def testOneFile(self):
        sync = Sync()
        self.rmFile(self._trgFile1)
        self.rmDir(self._trgFile1)
        self.mkDir(self._trgFile1)
        sync.oneFile(self._srcFile1, self._trgFile1)
        sync.close()
        
    def testFormatSize(self):
        sync = Sync()
        self.assertEquals('0 Byte', sync.formatSize(0))
        self.assertEquals('999 Byte', sync.formatSize(999))
        self.assertEquals('1.000 kByte', sync.formatSize(1000))
        self.assertEquals('999.999 kByte', sync.formatSize(999999))
        self.assertEquals('999.999 MByte', sync.formatSize(999999000))
        self.assertEquals('1.999 GByte', sync.formatSize(1.999E9))

    def testGetSettings(self):
        obj = SearchCriteria()
        self.assertEquals('', obj.getSettings())
        
        
    def testMakeReport(self):
        sync = Sync()
        sync._total._countDirs = 20
        sync._total._countFiles = 1024
        sync._total._sizeFiles = 100100100
        sync._modified._countDirs = 5
        sync._modified._countFiles = 20
        sync._modified._sizeFiles = 100100
        fn = sync.makeReport()
        sync.close()
        self.assertEquals(False, fn == None)
        self.log('Report in ' + fn)
        
    def testError(self):
        sync = Sync()
        sync._settings._maxFirstErrors = 2
        sync._settings._maxLastErrors = 1
        sync._settings._browser = '/usr/bin/konqueror'
        count = sync._settings._maxFirstErrors + 3 + sync._settings._maxLastErrors
        self.log('expecting {} errors'.format(count))
        for no in xrange(count):
            sync.error('Error No ' + str(no + 1))
        fn = sync.makeReport()
        sync.close()
        sync.showInBrowser(fn)
        self.assertEqual(count, sync._countErrors)
        self.assertEquals(sync._settings._maxFirstErrors, len(sync._firstErrors))
        self.assertEquals(sync._settings._maxLastErrors, len(sync._lastErrors))
     
    def testReplaceVariables(self):
        sync = Sync()
        timepointTuple = (2013, 2, 9, 7, 8, 3, 0, 0, 0)
        timepoint = time.mktime(timepointTuple)
        self.assertEquals("2013.02.09",
            sync.replaceVariables("{year}.{month}.{dayOfMonth}", timepoint))
        self.assertEquals("07:08:03",
            sync.replaceVariables("{hour}:{minute}:{second}", timepoint))
        self.assertEquals("week_05 Sat",
            sync.replaceVariables("week_{week} {dayOfWeek}", timepoint))
           
    def testMain(self):
        self.removeTarget()
        path = self._trg + self._lastNode + os.sep
        if not os.path.exists(path):
            os.makedirs(path)
        fn = path + 'mustBeDeleted.dat';
        self.mkFile(fn, 'yes')
        argv=[ # "testprog", 
              "-a",
              "-c", self._configFile,
              "-l", self._logFile,
              "--delete",
              "-m", "3",
              "-p", "*,-*.bak",
              "-s",
              "-u",
              "-vv",
              self._src,
              self._trg
              ]
        self.assertEquals(0, main(argv))
        self.assertFalse(os.path.exists(fn))
        
        argv=[ # "testprog", 
              "--add",
              "--config=" + self._configFile,
              "--delete",
              "--log-file=" + self._logFile,
              "--node-patterns", "*,-*.bak",
              "--dir-patterns", "*,-tmp,-temp,-cache",
              "--max-depth=3",
              "--size",
              "--update",
              "--use-last-node",
              "--verbose",
              self._src,
              self._trg
              ]
        self.assertEquals(0, main(argv))

    def testMainExit(self):
        argv=[ # "testprog", 
              "--add",
              "--config=" + self._configFile,
              "--delete",
              "--log-file=" + self._logFile,
              "--node-patterns", "*,-*.bak",
              "--dir-patterns", "*,-tmp,-temp,-cache",
              "--max-depth=3",
              "--report",
              "--size",
              "--update",
              "--use-last-node",
              "--verbose",
              self._src,
              self._trg
              ]
        try:
            self.assertEquals(0, main(argv))
            self.fail('report without browser')
        except SystemExit:
            pass

class DummyArgs:
    def __init__(self, pairs):
        for pair in pairs:
            (key, value) = re.split(":", pair)
            self.__dict__[key] = value
    
            

if __name__ == "__main__":
    #import sys;sys.argv = ['', 'Test.testName']
    unittest.main()