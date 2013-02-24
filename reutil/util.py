# Project: https://github.com/republib/republib/wiki
# Licence: Public domain: http://www.wtfpl.net
import sys, os, os.path

def exceptionString(excInfo, additionalInfo = None):
    '''Extracts the info as string from an exception info.
    @param excInfo:    the info given by sys.exc_info
    @return the info string
    '''
    exc = excInfo[1]
    rc = str(exc)
        
    if additionalInfo != None and rc.find(additionalInfo) < 0:
        rc += ': ' + additionalInfo
    return rc
        
def say(msg, newline=True):
    if newline:
        msg += "\n"
    sys.stdout.write(msg)
    
def sayError(msg, newline=True):
    if newline:
        msg += "\n"
    sys.stdout.write(msg)

class Util:
    '''Only static methods for some common actions.
    '''
    @staticmethod
    def writeFile(path, content=None):
        '''Creates a regular file.
        @param path: the file's name (with path)
        @param content: None or the file's content
        '''
        fp = open(path, "w")
        if content != None:
            fp.write(content);
        fp.close()
    
    @staticmethod
    def readFileAsString(path):
        '''Reads a file into a string.
        @param path: the file's name (with path)
        @return: None: file not readable.<br>
                otherwise: the file's content
        '''
        rc = None
        fp = open(path, "r")
        if fp != None:
            rc = fp.read()
        fp.close()
        return rc
    
    @staticmethod
    def mkDir(name):
        '''Ensures that a subdirectory exists.
        If not it will be created.
        @param name: the subdirectory's name
        '''
        if not os.path.exists(name):
            os.makedirs(name)
    
    @staticmethod
    def getTempDir(node = None, endsWithSeparator=False):
        '''Returns a temporary directory.
        @param node: None of the subdirectory in the standard temporary dir
        @param endsWithSeparator: True: the result ends with the separator
        @return: the name of an existing temporary directory
        '''
        rc = None
        if 'TEMP' in os.environ:
            rc = os.environ['TEMP']
        if (rc == None or not os.path.exists(rc)) and 'TMP' in os.environ:
            rc = os.environ['TMP']
        if rc == None or not os.path.exists(rc):
            rc = '/tmp' if os.sep == '/' else 'c:\\temp'
        if node != None:
            rc += os.sep + node
            if not os.path.exists(rc):
                os.mkdir(rc)
        if endsWithSeparator and not rc.endswith(os.sep):
            rc += os.sep
        return rc
    
    @staticmethod
    def getTempFile(node, subdir = None):
        '''Returns a file name in a temporary directory.
        @param node: name of the file without path
        @param subdir: None of the subdirectory where the file is laying
        @return: the name of a file in the temporary directory
        '''
        rc = Util.getTempDir(subdir, True) + node
        return rc
