import logging, os.path

class Config:
    '''Maintenances a dictionary read from file(s).'
    The format of the file:<br>
    CONFIG ::= LINE*<br>
    LINE ::= INCLUDE | ASSIGNMENT | COMMENT<br>
    INCLUDE ::= 'include' FILE<br>
    ASSIGNMENT ::= VARIABLE '=' VALUE<br>

    Example:<br>
    # Configuration for evironment variables
    share:reset
    include "/etc/global_var.conf"
    global.basedir=/etc
    '''
    def __init__(self, filename):
        '''Constructor.
        @param filename: the configuration file
        '''
        self._dict = {}
        self._files = []
        self.read(filename)

    def read(self, filename):
        '''Reads a configuration file.
        @param filename: the configuration file
        '''
        fp = open(filename, "r")
        lineNo = 0
        for line in fp:
            line = line.rstrip()
            lineNo += 1
            if not line.startswith('include'):
                ix = line.find('=')
                if ix > 0 and line[0].isalpha():
                    self._dict[line[0:ix]] = line[ix+1:]
            else:
                name = line[7:].strip(" \t\"'")
                if name not in self._files:
                    self._files.append(name) 
                    if os.path.exists(name):
                        self.read(name)
                    else:
                        logging.error(filename + '-' + str(lineNo) 
                            + ': can not include: ' + name)
        fp.close()
        
    def get(self, key):
        '''Returns a configuration value.
        @param key: the key of the value
        @return None: invalid key<br>
                otherwise: the value belonging to the key
        '''
        return self._dict[key] if key in self._dict else None 
        