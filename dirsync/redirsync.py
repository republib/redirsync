#!/usr/local/bin/python
# encoding: utf-8
# Project: https://github.com/republib/republib/wiki
# Licence: Public domain: http://www.wtfpl.net

'''
dirsync.redirsync -- syncronization of two directory trees

dirsync.redirsync is a program which synchronizes two directory
trees. Depending on the given options new or modified files
will be copied from the source to the destination.

@author:     hamatoma
        
@copyright:  2013 republib. No rights reserved.
        
@license:    Public domain: http://www.wtfpl.net

@contact:    republib@gmx.de
@deffield    updated: Updated
'''

import os.path, shutil, stat, re, fnmatch, logging, time, math, subprocess

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
from argparse import ArgumentTypeError
from reutil.util import *
from reutil.config import Config


__all__ = []
__version__ = 0.1
__date__ = '2013-02-06'
__updated__ = '2013-02-06'

DEBUG = 1
TESTRUN = 0
PROFILE = 0

class SearchCriteria:
    '''Administrates the search criteria for a filename pattern matching.
    '''
    def __init__(self):
        '''Constructor.
        '''
        self._includeAll = False
        self._includeEndsWith = []
        self._includePatterns = []
        self._excludeEndsWith = []
        self._excludePatterns = []
        self._wildcardMatcher = re.compile(r'[*?\[\]]')
   
    def getSettings(self):
        '''Returns a string containing the current search criteria.
        @return: a human readable string
        '''
        opts = ' '
        if self._includeAll:
            opts = '*,'
        for item in self._includeEndsWith:
            opts += '*' + item + ','
        for item in self._includePatterns:
            opts += item + ','
        for item in self._excludeEndsWith:
            opts += '-*' + item + ','
        for item in self._excludePatterns:
            opts += '-' + item + ','
        return opts[:-1]
        
    def hasWildcards(self, item):
        '''Tests whether a string contains wildcards.
        @param item: the item to inspect
        @return: True: the item contains at least one wildcard.<br>
                False: otherwise
        '''
        rc = self._wildcardMatcher.search(item)
        return rc != None
    
    def addPatterns(self, patterns):
        '''Adds a each entry of a list to the include/exclude criteria
        @param patterns: the list of patterns
        '''
        for entry in patterns:
            if entry.startswith('-'):
                if entry.startswith('-*') and not self.hasWildcards(entry[2:]):
                    self._excludeEndsWith.append(entry[2:])
                else:
                    self._excludePatterns.append(entry[1:])
            else:
                if entry == '*':
                    self._includeAll = True
                elif entry.startswith('*') and not self.hasWildcards(entry[1:]):
                    self._includeEndsWith.append(entry[1:])
                else:
                    self._includePatterns.append(entry)

    def matches(self, name):
        '''Tests whether a name matches the search criteria.
        @param name: the name to test
        @return: True: the name matches the criteria.<br>
               False: otherwise
        '''
        rc = self._includeAll
        if not rc:
            for pattern in self._includeEndsWith:
                if name.endswith(pattern):
                    rc = True
                    break
            if not rc:
                for pattern in self._includePatterns:
                    if fnmatch.fnmatch(name, pattern):
                        rc = True
                        break
        if rc:
            for pattern in self._excludeEndsWith:
                if name.endswith(pattern):
                    rc = False
                    break
            if rc:
                for pattern in self._excludePatterns:
                    if fnmatch.fnmatch(name, pattern):
                        rc = False
                        break
        return rc

class Settings:
    '''Stores the search criteria for files and subdirs.
    '''
    def __init__(self):
        self._node = SearchCriteria()
        self._dir = SearchCriteria()
        self._deleteFilesWithoutSource = False
        self._maxDepth = 99
        self._addNonExisting = False
        self._copyNewer = False
        self._copyDifferentSize = False
        self._speed = 'quick'
        self._verboseLevel = 1
        self._showHtml = False
        self._maxFirstErrors = 20
        self._maxLastErrors = 20
             
    def readConfig(self, filename):
        '''Reads the configuration file.
        @param filename: the name of the configuration file
        '''
        config = Config(filename)
        mode = config.get('copy.mode')
        if mode:
            if mode.find('add'):
                self._addNonExisting = True
            if mode.find('size'):
                self._copyDifferentSize = True
            if mode.find('update'):
                self._copyNewer = True
            if mode.find('delete'):
                self._deleteFilesWithoutSource = True
        mode = config.get('copy.mode.removed')
        if mode:
            if mode.find('add'):
                self._addNonExisting = False
            if mode.find('size'):
                self._copyDifferentSize = False
            if mode.find('update'):
                self._copyNewer = False
            if mode.find('delete'):
                self._deleteFilesWithoutSource = False
        maxDepth = config.get('maxDepth')
        if maxDepth != None:
            self._maxDepth = int(maxDepth)
        verbose = config.get('verboseLevel')
        if verbose != None:
            self._verboseLevel = int(verbose)
        
        
    def getFromOpts(self, opts):
        '''Get the settings from the command line options.
        @param opts: the command line options
        '''
        self._addNonExisting = opts.add
        self._copyNewer = opts.update
        self._copyDifferentSize = opts.size
        self._maxDepth = opts.maxDepth
        self._deleteFilesWithoutSource = opts.delete
        self._node.addPatterns(re.split(r',', opts.nodePatterns))
        self._dir.addPatterns(re.split(r',', opts.dirPatterns))
        self._speed = opts.speed
        self._verboseLevel = opts.verbose
        self._showHtml = opts.report
        
    def getSettings(self):
        opts = ''
        if self._copyNewer:
            opts += " --add"
        if self._deleteFilesWithoutSource:
            opts += "--delete"
        if self._copyNewer:
            opts += " --update"
        opts += "--max-depth=" + str(self._maxDepth)
        opts += " --node-patterns=" + self._node.getSettings()
        opts += " --dir-patterns=" + self._dir.getSettings()
        return opts
        
class Statistics:
    '''Statistic data about a directory tree.
    '''
    def __init__(self):
        '''Constructor.
        '''
        self._countDirs = 0
        self._countFiles = 0
        self._sizeFiles = 0
        
class Sync:
    '''Synchronizes two directory trees in an efficient way.
    different files will transfered from the source to the target.
    ''' 
    def __init__(self):
        '''Constructor.
        @param opts: options and arguments from the command line
        '''
        self._startTime = time.time()
        self._settings = Settings()
        self._settingStack = []
        self._countTotals = True
        self._localConfig = '.redirsync.conf'
        self._total = Statistics()
        self._completed = Statistics()
        self._modified = Statistics()
        self._writableFile = None
        self._fpError = None
        self._fnError = None
        self._countErrors = 0
        self._firstErrors = []
        self._lastErrors = []
        self._home = None
        self._waitingErrors = []
        self._browser = None
        if 'REDIRSYNC_HOME' in os.environ:
            self._home = os.environ.get('REDIRSYNC_HOME')
        elif 'HOME' in os.environ:
            self._home = os.environ.get('HOME')
        if self._home == None:
            if os.sep == '/':
                self._home = '/home/' +  os.getlogin()
            else:
                self._home = 'c:\\config'
        if not os.path.exists(self._home) or not os.path.isdir(self._home):
            self._waitingErrors.append('home directory does not exist: ' 
                + self._home)

    def replaceVariables(self, phrase, timepoint = None):
        '''Replaces variables in a string with its values.
        @param phrase: the string which should be changed
        @param timepoint: the time used by the time variables
        @return: None: the phrase is None<br>
                the string with replaced variables
        '''
        rc = phrase
        if rc:
            rc = rc.replace('{home}', self._home)
            if timepoint == None:
                timepoint = time.time()
            now = time.localtime(timepoint)
            rc = rc.replace('{year}', str(now[0]))
            rc = rc.replace('{month}',  "{:02d}".format(now[1]))
            rc = rc.replace('{dayOfMonth}',  "{:02d}".format(now[2]))
            rc = rc.replace('{hour}', "{:02d}".format(now[3]))
            rc = rc.replace('{minute}',  "{:02d}".format(now[4]))
            rc = rc.replace('{second}',  "{:02d}".format(now[5]))
            
            rc = rc.replace('{dayOfWeek}', time.strftime("%a", now))
            rc = rc.replace('{week}', time.strftime("%W", now))
            rc = rc.replace('{time}', "%d" % (timepoint))
        return rc

    def readMasterConfig(self, config):
        '''Reads the master configuration file.
        @param config: None or the name of the configuration file (with path)
        '''
        if config == None:
            config = self._home + os.sep + '.redirsync.conf'
        if not os.path.exists(config):
            self._waitingErrors.append('Configuration file not found: ' + config)
        else:
            self._settings.readConfig(config)
            self._browser = config.get('browser')
            self._fnError = self.replaceVariables(config.get('log.file.error'))
            self._fnLog = self.replaceVariables(config.get('log.file'))

            if self._fnError == None:
                self._fnError = Util.getTempFile('redirsync.error.log')
        for msg in self._waitingErrors:
            self.error(msg)
        
    def close(self):
        '''Frees the resources.
        '''
        if self._writableFile != None:
            os.remove(self._writableFile)
        if self._fpError != None:
            self._fpError.close()
    
    def log(self, msg):
        '''Prints a message to the log media.
        @param msg: the message to issue
        '''
        sys.stdout.write(msg + "\n")
        
    def error(self, msg, exception = None, additional = None):
        '''Prints a message to the log media.
        @param msg:         the message to issue
        @param exception:    the exception describing the error
        @param additional:    if the exception message does not contain this
                                string, it will be issued
        '''
        msg += "\n"
        self._countErrors += 1
        if self._countErrors <= self._settings._maxFirstErrors:
            self._firstErrors.append(msg)
        self._lastErrors.append(msg)
        if len(self._lastErrors) > self._settings._maxLastErrors:
            self._lastErrors = self._lastErrors [1:]
        if exception != None:
            if not  msg.endswith(" "):
                msg += " "
            error = repr(exception)
            msg += error
            if additional != None and error.find(additional) < 0:
                msg += " [" + additional + ']'
        sys.stderr.write(msg )
        if self._fpError == None and self._fnError != None:
            self._fpError = open(self._fnError, "w")
        if self._fpError != None:
            self._fpError.write(msg)
        
    def addNodePatterns(self, patterns):
        '''Adds a each entry of a list to the include/exclude criteria of the node
        @param patterns: the list of patterns to work
        '''
        self._settings._node.addPatterns(patterns)
                
    def addDirPatterns(self, patterns):
        '''Adds a each entry of a list to the include/exclude criteria of the dir
        @param patterns: the list of patterns to work
        '''
        self._settings._dir.addPatterns(patterns)
                
    
    def deleteFile(self, full):
        '''Deletes a file.
        @param full: the filename with path
        '''
        if self._settings._verboseLevel > 1:
            self.log('-' + full)
        try:
            os.unlink(full)
        except Exception as e:
            self.error('remove failed: ', e, full)
       
    def onTreeError(self, function, path, exceptionInfo):
        '''A callback function for rmtree().
        @param function: isLink(), ...
        @param path: the name of the file/subdir where the error has been occurred
        @param exceptionInfo: more info about the error
        '''
        self.error('cannot remove: ' + exceptionString(exceptionInfo, path))
    
    def getWritableFile(self):
        '''Returns a file which is writable.
        This file can be used as source for a file attribute copy.
        @return: the name of a file which is writable
        '''
        if self._writableFile == None:
            self._writableFile = os.tempnam()
            fp = open(self._writableFile, "w")
            fp.close()
        return self._writableFile
            
    def rmTree(self, path):
        '''Removes a directory with all files and subdirectories.
        @param path: the full name of the directory to delete
        '''
        if not path.endswith(os.sep):
            path += os.sep
        try:  
            fullName = path      
            for node in os.listdir(path):
                fullName = path + node
                statInfo = os.lstat(fullName)
                try:
                    self.makeWritable(fullName, statInfo)
                    if self._settings._verboseLevel > 1:
                        self.log('-' + fullName)
                    if stat.S_ISDIR(statInfo.st_mode):
                        self.rmTree(fullName + os.sep)
                    else:
                        os.unlink(fullName)
                except Exception as exc:
                    self.error('cannot remove: ', exc, fullName)
            os.rmdir(path)
        except Exception as exc:
            self.error('cannot remove: ', exc, fullName)
       
    def makeWritable(self, path, statInfo = None):
        '''Ensures that a file (or subdirectory) is writable.
        @param path: the filename
        @param statInfo: None of the status info of the file.<br>
                        If None the info will be retrieved
        '''
        if statInfo == None:
            statInfo = os.lstat(path)
        mode = statInfo.st_mode & (stat.S_IWUSR + stat.S_IWGRP + stat.S_IWOTH)
        if mode == 0:
            try:
                shutil.copymode(self.getWritableFile(), path)
            except Exception as exc:
                self.error('cannot make writable: ', exc, path)    
    
    def showInBrowser(self, filename):
        '''Shows a file in a browser.
        @param filename: the file to show
        '''
        if self._settings._browser != None:
            subprocess.call([self._settings._browser, filename])
        
    def oneFile(self, fullSrc, fullTrg, srcStat = None, trgStat = None):
        '''Synchronizes one file.
        @param fullSrc: the full path of the source file
        @param fullTrg: the full path of the target file
        @param srcStat: None or the status of the source
        @param srcStat: None or the status of the target
        '''
        copyReason = None
        if srcStat == None:
            srcStat = os.lstat(fullSrc)
            if os.path.exists(fullTrg):
                trgStat = os.lstat(fullTrg)
        if self._countTotals:
            self._total._sizeFiles += srcStat.st_size
            self._total._countFiles += 1
            
        if trgStat == None:
            if self._settings._addNonExisting:
                copyReason = "+"
        else:
            if stat.S_ISDIR(trgStat.st_mode):
                self.makeWritable(fullTrg, trgStat)
                self.rmTree(fullTrg)
                copyReason = '~'
            if not self._settings._copyNewer:
                copyReason = '*'
            elif self._settings._copyNewer and srcStat.st_mtime > trgStat.st_mtime:
                aType = type(srcStat.st_mtime)
                if (aType == type(float) 
                      and srcStat.st_mtime - trgStat.st_mtime < 1/(24*3600)):
                    copyReason = '>'
            elif self._settings._copyDifferentSize and srcStat.st_size != trgStat.st_size:
                copyReason = '!'
            if copyReason != None:
                self.makeWritable(fullTrg, trgStat)
        if copyReason != None:
            if self._settings._verboseLevel > 1:
                self.log(copyReason + fullTrg)
            shutil.copy2(fullSrc, fullTrg)
            self._modified._sizeFiles += srcStat.st_size
            self._modified._countFiles += 1
        
    def oneDir(self, src, trg, depth):
        '''Syncronizes one directory.
        @param src: the source directory, e.g. /home/
        @param trg: the target directory e.g. /opt/backup/
        @param depth: the current depth of the source tree
        '''
        if not os.path.exists(trg):
            if self._settings._verboseLevel > 1:
                self.log('&' + trg)
            os.mkdir(trg)
            
        files = os.listdir(src)
        if self._localConfig in files:
            self.readConfig(src + self._localConfig) 
        validFiles = []
        dirs = []
        if self._countTotals:
            self._total._countDirs += 1
        self._modified._countDirs += 1
        modified = self._modified._countFiles
        for filename in files:
            fullSrc = src + filename
            srcStat = os.lstat(fullSrc)
            if stat.S_ISDIR(srcStat.st_mode):
                if self._settings._dir.matches(filename):
                    dirs.append(filename)
            else:
                self._completed._countFiles += 1
                self._completed._sizeFiles += srcStat.st_size
                fullTrg = trg + filename
                if self._settings._node.matches(filename):
                    if self._settings._deleteFilesWithoutSource:
                        validFiles.append(filename) 
                    trgStat = os.lstat(fullTrg) if os.path.exists(fullTrg) else None
                    if not stat.S_ISDIR(srcStat.st_mode):
                        self.oneFile(fullSrc, fullTrg, srcStat, trgStat)
        self._completed._countDirs += 1               
        if modified != self._modified._countFiles:
            self._modified._countDirs += 1
            
        if self._settings._deleteFilesWithoutSource:
            trgFiles = os.listdir(trg)
            for filename in trgFiles:
                if filename not in validFiles and filename not in dirs:
                    full = trg + filename
                    if os.path.isdir(full):
                        self.rmTree(full)
                    else:
                        self.deleteFile(full) 
                        
        if depth <= self._settings._maxDepth:
            for subdir in dirs:
                fullTrg = fullTrg + subdir
                if os.path.exists(fullTrg) and not os.path.isdir(fullTrg):
                    self.deleteFile(fullTrg)
                self.oneDir(src + subdir + os.sep, trg + subdir + os.sep, 
                    depth + 1)
         
            
    def synchronize(self, sources, target, useLastNode):
        '''Synchronizes the directory trees given by the command line opts.
        @param sources: a list of source directories
        @param target: the name of the target directory
        @param useLastNode: True: the last node of the source will be appended
                        to the target. source=/x/y target=/z copy target: /z/y
        '''
        target = self.replaceVariables(target, self._startTime)
        for src in sources:
            if not src.endswith(os.sep):
                src += os.sep
            trg = target
            if not trg.endswith(os.sep):
                trg += os.sep
            if useLastNode:
                lastNode = src[:-1]
                if len(lastNode) == 0:
                    self.error("--use-last-node needs at least one node in source " + src)
                trg += os.path.basename(lastNode) + os.sep
            if self._settings._verboseLevel > 0:
                self.log("=== " + src + " -> " + trg)
            self.oneDir(src, trg, 0)
        if self._settings._showHtml:
            report = self.makeReport()
            self.showInBrowser(report)

    def formatSize(self, bytes):
        '''Formats a size value in a human readable form.
        @param bytes    the size in bytes
        @return the formated string
        '''
        if bytes < 1000:
            rc = str(bytes) + ' Byte'
        elif bytes < 1000 * 1000:
            rc = "%.3f kByte" % (bytes / 1000.0)
        elif bytes < 1000 * 1000 * 1000:
            rc = "%.3f MByte" % (bytes / 1000.0 / 1000.0)
        else:
            rc = "%.3f GByte" % (bytes / 1000.0 / 1000.0 / 1000.0)
        return rc
    
    def makeReport(self):
        '''Builds a report in HTML and write it to a file.
        @returns: the filename
        '''
        filename = Util.getTempFile("redirsync_%d.html" % (time.time()), None)
        fp = open(filename, "w")
        endTime = time.time()
        durationInt = int(endTime - self._startTime)
        if durationInt < 60:
            duration = str(durationInt) + ' sec'
        elif durationInt < 3600:
            duration = "%d:%02d [min:sec]" % (int(durationInt / 60), durationInt % 60)
        else:
            duration = "%d:%02d:%02d [std:min:sec]" % (
                int (durationInt / 3600), int(durationInt / 3600) % 60, durationInt % 60)
            
        errors = ''
        if self._countErrors > 0:
            errors = """
<h2>Es sind leider Fehler aufgetreten</h2>
<p>Anzahl Fehler: {}
<p><a href="file://{}">Vollst&auml;ndiges Fehlerprotokoll</a></p>
<pre>
""".format(self._countErrors, self._fnError) + "".join(self._firstErrors)
                
            omitted = self._countErrors - (self._settings._maxFirstErrors 
                + self._settings._maxLastErrors)
            if omitted > 0:
                errors += "... ({} Fehler ausgelassen)\n".format(omitted)
            errors += "".join(self._lastErrors) + "</pre>\n"
        msg = '''<html>
<head>
<title>Datensicherung Report</title>
<body>
<h1>Datensicherung abgeschlossen</h1>
<p>Start: {start}<br/>
Dauer: {duration}</p>
<table border="0">
<tr><td>&nbsp;</td>
    <td>Verzeichnisse</td>
    <td>Dateien</td>
    <td>MByte</td>
</tr>
<tr><td>Gesamt:</td>
    <td>{t_dir}</td>
    <td>{t_files}</td>
    <td>{t_size}</td>
</tr>
<tr><td>Ge&auml;ndert:</td>
    <td>{m_dir}</td>
    <td>{m_files}</td>
    <td>{m_size}</td>
</tr>
<tr><td>Rate:</td>
    <td>{r_dir}:1</td>
    <td>{r_files}:1</td>
    <td>{r_size}:1</td>
</tr>
</table>
{errors}
</body>
</html>
        '''.format(
            start=time.strftime('%d.%m.%y %H:%M:%S', time.localtime(self._startTime)), 
            duration=duration, 
            t_dir=self._total._countDirs, 
            t_files=self._total._countFiles, 
            t_size=self.formatSize(self._total._sizeFiles),
            m_dir=self._modified._countDirs, 
            m_files=self._modified._countFiles, 
            m_size=self.formatSize(self._modified._sizeFiles),
            r_dir=self._total._countDirs / max(1, self._modified._countDirs),
            r_files=self._total._countFiles / max(1, self._modified._countFiles),
            r_size=self._total._sizeFiles / max(1, self._modified._sizeFiles),
            rate=self._modified._sizeFiles / max(1,durationInt),
            errors=errors)
        fp.write(msg)
        fp.close()
        return filename

class CLIError(Exception):
    '''Generic exception to raise and log different fatal errors.'''
    def __init__(self, msg):
        super(CLIError).__init__(type(self))
        self.msg = "E: %s" % msg
    def __str__(self):
        return self.msg
    def __unicode__(self):
        return self.msg

def isDirectory(path):
    if not os.path.exists(path):
        raise ArgumentTypeError("directory does not exist: " + path)
    if not os.path.isdir(path):
        raise ArgumentTypeError(path + " is a file, not a directory")
    return path

def isFile(path):
    if not os.path.exists(path):
        raise ArgumentTypeError("file does not exist: " + path)
    if os.path.isdir(path):
        raise ArgumentTypeError(path + " is a directory, not a file")
    if not os.path.isfile(path):
        raise ArgumentTypeError(path + " is not a regular file")
    return path

def main(argv=None): # IGNORE:C0111
    '''Command line options.'''
    
    if argv is None:
        argv = sys.argv[1:]

    program_name = os.path.basename(sys.argv[0])
    program_version = "v%s" % __version__
    program_build_date = str(__updated__)
    program_version_message = '%%(prog)s %s (%s)' % (program_version, program_build_date)
    program_shortdesc = "sychronizes  directory trees"
    program_license = '''%s

  Created by hamatoma %s.
  Copyright 2013 REal PUBlic LIBrary. 2013 republib. No rights reserved.
  
  This is public domain. You can do, what you want.
  
  Distributed on an "AS IS" basis without warranties
  or conditions of any kind, either express or implied.

USAGE
''' % (program_shortdesc, str(__date__))

    try:
        isLinux = os.sep == '/'
        if isLinux:
            defaultLog = "/var/log/redirsync.log"
            defaultConfig = "~/.redirsync.conf"
        else:
            defaultLog = "c:\\redirsync\\redirsync.log"
            defaultConfig = "c:\\redirsync\\redirsync.conf"
            
        # Setup argument parser
        parser = ArgumentParser(description=program_license, formatter_class=RawDescriptionHelpFormatter)
        parser.add_argument("-a", "--add", dest="add", action="store_true", help="add new files (only exist on the source")
        parser.add_argument("-c", "--config", dest="config", type=isFile, help="configuration file. [default: {}]".format(defaultConfig) )
        parser.add_argument("--delete", dest="delete", action="store_true", help="files on the target which are not exist on the source will be deleted")
        parser.add_argument("-l", "--log-file", dest="logfile", default=defaultLog, help="log file. [default: %(default)s]")
        parser.add_argument("-m", "--max-depth", dest="maxDepth", type=int, default=100, help="maximal depth of the directory tree.  [default: %(default)s]" )
        parser.add_argument("-p", "--node-patterns", dest="nodePatterns", default="*,-*.bak,-*~", help="only files matching this patterns will be copied. Separator: ',' [default: %(default)s]", metavar="RE")
        parser.add_argument("-P", "--dir-patterns", dest="dirPatterns", default="*,cache,-temp,-tmp", help="only files matching this patterns will be copied. Separator: ',' [default: %(default)s]", metavar="RE")
        parser.add_argument("-r", "--report", dest="report", action="store_true", help="displays a report in a browser. [default: %(default)s]")
        parser.add_argument("-s", "--size", dest="size", action="store_true", help="copy if the size of source and target is different. [default: %(default)s]")
        parser.add_argument("-S", "--speed", dest="speed", default="quick", help="'quick' or 'save'. [default: %(default)s]")
        parser.add_argument("-u", "--update", dest="update", action="store_true", help="if a file exists on the destination and it is newer it will be copied")
        parser.add_argument("--use-last-node", dest="useLastNode", action="store_true", help="the last node of the source will added to the target.  [default: %(default)s]")
        parser.add_argument("-v", "--verbose", dest="verbose", action="count", help="set verbosity level [default: %(default)s]")
        parser.add_argument('-V', '--version', action='version', version=program_version_message)
        parser.add_argument(dest="source", type=isDirectory, help="source directory", metavar="source", nargs='+')
        parser.add_argument(dest="target", type=isDirectory, help="target directory", metavar="target")
        
        # Process arguments
        args = parser.parse_args(argv)
        
        if ("config" not in args and os.path.isfile(defaultConfig) ):
            args.append["config"] = defaultConfig
        
        sync = Sync()
        sync._settings.getFromOpts(args)
        if sync._settings._showHtml and (not hasattr(sync._browser, '_browser')
                or sync._browser == None):
            sync.error('No browser defined. I cannot execute --report')
            exit(2)
        
        if args.verbose:
            sources = ""
            for src in args.source :
                sources += " " + src        
            say("source paths:" + sources)
            say( "destination: " + args.target)
            opts = ""
            if args.logfile:
                opts += " --logfile=" + args.logfile
            if args.useLastNode:
                opts += " --use-last-node"
            say("opts: " + opts + ' ' + sync._settings.getSettings())
        
        sync.synchronize(args.source, args.target, args.useLastNode)
        sync.close()

           
        return 0
    except KeyboardInterrupt:
        ### handle keyboard interrupt ###
        return 0
    except Exception as e:
        if DEBUG or TESTRUN:
            raise(e)
        indent = len(program_name) * " "
        sys.stderr.write(program_name + ": " + repr(e) + "\n")
        sys.stderr.write(indent + "  for help use --help")
        return 2

if __name__ == "__main__":
    if DEBUG:
        #sys.argv.append("-h")
        sys.argv.append("-v")
        #sys.argv.append("-r")
    if TESTRUN:
        import doctest
        doctest.testmod()
    if PROFILE:
        import cProfile
        import pstats
        profile_filename = 'dirsync.redirsync_profile.txt'
        cProfile.run('main()', profile_filename)
        statsfile = open("profile_stats.txt", "wb")
        p = pstats.Stats(profile_filename, stream=statsfile)
        stats = p.strip_dirs().sort_stats('cumulative')
        stats.print_stats()
        statsfile.close()
        sys.exit(0)
    sys.exit(main())