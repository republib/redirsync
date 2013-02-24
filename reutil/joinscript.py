# Project: https://github.com/republib/republib/wiki
# Licence: Public domain: http://www.wtfpl.net
import re, sys, os.path
from util import sayError

class ScriptMaker:
    '''Joins multiple python modules into a single script.
    '''
    def __init__(self, script, modules):
        '''Constructor.
        @param script: name of the result script. With path
        @param modules: list of modules to join
        '''
        self._script = script
        self._modules = modules
        self._fpScript = open(self._script, "w")
        self._importMatcher = re.compile(r'from ([a-z0-9.]+) import')
        self._importModules = []
        for module in self._modules:
            if not os.path.exists(module):
                usage('file not found: ' + module)
            if not module.endswith('.py'):
                usage('not a python source file: ' + module)
            # ".py" abschneiden:
            module = module[0:-3]
            self._importModules.append(module.replace("/", '.').replace("\\", '.'))

    def close(self):
        '''Frees the resouces.
        '''
        self._fpScript.close()
        
    def isModuleImport(self, line):
        '''Tests whether the line is an import of a joined module.
        @param line: the line to test
        @return: True: the line is an import of one of the joined module
        '''
        rc = False
        matcher = self._importMatcher.match(line)
        if matcher:
            module = matcher.group(1)
            rc = module in self._importModules
        return rc
    
    def readModule(self, name, isMainModule):
        '''Reads the content of one python module and write it to the script.
        @param name: the filename with path
        @param isMainModule: True: the module contains the main section.
        '''
        inp = open(name, "r")
        for line in inp:
            if not isMainModule and line.startswith("if __name__ == '__main__'"): 
                break
            if not self.isModuleImport(line):
                self._fpScript.write(line)
        inp.close()
         
    def build(self):
        '''Builds the script.
        '''
        for module in self._modules[1:]:
            self.readModule(module, False)
        self.readModule(self._modules[0], True)
        
def usage(msg):
    '''Print a usage message and an error message
    @param msg: the error message
    '''
    sayError("usage: joinscript <scriptname> <module_main> <module_2> ...\n+++ " 
        + msg)
    sys.exit(1)
    
if __name__ == '__main__':
    if len(sys.argv) < 1 + 3:
        usage("too few args")
    script = sys.argv[1]
    maker = ScriptMaker(sys.argv[1], sys.argv[2:])   
    maker.build()
    maker.close()