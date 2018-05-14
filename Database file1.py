# -*- coding: utf-8 -*-
import time
import numpy as np
import os
import sys


class nsd_base:
    '''# NSD_BASE - A node that fits into an NSD_BASE_BRANCH'''

    def __init__(self, filename='', command=''):
        ''' __INIT__ - Creates a named NSD_BASE object
        Creates an NSD_BASE object. Each NSD_BASE object has a unique
        identifier that is stored in the property 'objectfilename'. The class
        includes methods for writing and reading object files in a platform- and
        language-independent manner.
        
        In an alternate construction, one may call
        
        OBJ = NSD_BASE(FILENAME, COMMAND)
        with COMMAND set to 'OpenFile', and the object will be created by
        reading in data from the file FILENAME (full path). To developers:
        All NSD_BASE descendents must offer this 2 element constructor.
         
        See also: NSD_DBLEAF, NSD_BASE'''
        self._objectfilename_ = 'object_%s_%s'%(hex(int(time.time())), hex(np.random.randint(100000)))
        self.__lockfid__ = []
        if command.lower()=='openfile':
            self.readobjectfile(filename)
    
    def readobjectfile(self, filename):
        '''READOBJECTFILE - read the object from a file
        
        Reads the NSD_BASE_OBJ from the file FILENAME.
        
        The file format consists of several strings that are read in sequence.
        The first line is always the name of the object class.'''
        with open(filename, 'r') as fid: # files will consistently use big-endian
            classname = fid.readline()[:-1]
            if classname==type(self).__name__:
                # we have the right type of object
                [dummy,fn] = self.stringdatatosave()
                values = []
                i=1
                values.append('')
                while i<len(fn):
                    values.append(fid.readline()[:-1])
                    i=i+1
                self.setproperties(fn, values)
            else:
                raise Exception(['Not a valid NSD_BASE file:' + filename ])
        return self
    
    def deleteobjectfile(self, dirname):
        '''DELETEOBJECTFILE - Delete / remove the object file (or files) for NSD_BASE
        delete all files associated with NSD_BASE_OBJ in directory DIRNAME (full path).
        B is 1 if the process succeeds, 0 otherwise.'''
        filename = dirname+'/'+self._objectfilename_
        b=1
        try:
            os.remove(filename)
        except:
            b=0
        return b
    
    def setproperties(self, properties, values):
        '''SETPROPERTIES - set the properties of an NSD_BASE object 
        Given a cell array of string PROPERTIES and a cell array of the corresponding
        VALUES, sets the fields in NSD_BASE_OBJ and returns the result in OBJ.
       
        If any entries in PROPERTIES are not properties of NSD_BASE_OBJ, then that property is skipped.
        The properties that are actually set are returned in PROPERTIESSET.'''
        fn=vars(self)
        properties_set = []
        for i in range(len(properties)):
            if properties[i].startswith('$'):
                properties[i]='_'+properties[i][1:]+'_'
        for i in range(len(properties)):
            if properties[i] in fn:
               exec('self.'+properties[i]+'="'+values[i]+'"')
               properties_set.append(properties[i])
        return properties_set
           
    def writeobjectfile(self, dirname='', locked=0):
        '''WRITEOBJECTFILE - write the object file to a file	
        the NSD_BASE_OBJ to a file in a manner that can be
        the creator function NSD_BASE.
        Writes to the path DIRNAME/NSD_BASE_OBJ.OBJECTFILENAME
        If LOCKED is 1, then the calling function has verified a correct
        the file and WRITEOBJECTFILE shouldn't lock/unlock it.
        See also: NSD_BASE/NSD_BASE'''
        thisfunctionlocked = 0
        if not locked: # we need to lock it
            self.lock(dirname)
            thisfunctionlocked = 1
        filename = dirname+'/'+self._objectfilename_
        with open(filename, 'w') as fid:
            data,fieldnames = self.stringdatatosave()
            for i in range(len(data)):
                fid.write(data[i]+'\n')
        if thisfunctionlocked:
            self.unlock(dirname) 
            
    def stringdatatosave(self):
        '''STRINGDATATOSAVE - Returns a set of strings to write to file to save object information
        return a cell array of strings to save to the objectfilename.
        FIELDNAMES is a set of names of the fields/properties of the object that are being stored.
        For NSD_BASE, this returns the classname, name, and the objectfilename.'''
        data=[type(self).__name__,self._objectfilename_]
        fieldnames = [ '', '_objectfilename_' ]
        return data, fieldnames
    
    def lockfilename(self, dirname):
        '''LOCKFILENAME - the filename of the lock file that serves as a semaphore to maintain data integrity
        
        LOCKFNAME = LOCKFILENAME(NSD_BASE_OBJ, DIRNAME)
        
        Returns the filename that is used for locking the metadata and object data files.
        DIRNAME is the directory to use (full path).
        
        See also: NSD_BASE/LOCK NSD_BASE/UNLOCK NSD_BASE/LOCKFILENAME'''
        filename = dirname+'/'+self._objectfilename_
        lockfname = filename+'-lock'
        return lockfname
    
    def lock(self, dirname):
        '''LOCK - lock the metadata file and object files so other processes cannot change them
        
        Attempts to obtain the lock on the object file. If it is successful,
        B is 1. Otherwise, B is 0. DIRNAME is the directory where the file(s)
        is(are) stored (full path).
        
        Note: Only a function that calls LOCK should call UNLOCK to maintain integrety of object data.
        
        See also: NSD_BASE/LOCK NSD_BASE/UNLOCK NSD_BASE/LOCKFILENAME'''
        b = 0
        lockfid = checkout_lock_file(self.lockfilename(dirname))
        if lockfid!=-1:
            self.__lockfid__ = lockfid
            b=1
        return b
            
    def unlock(self, dirname):
        '''UNLOCK - unlock the metadata file and object files so other processes can change them
        Removes the lock file from the NSD_BASE NSD_BASE_OBJ.

        DIRNAME is the directory where the file(s) is (are) stored (full path).

        Note: Only a function that calls LOCK should call UNLOCK to maintain integrety of metadata and object data.
        the function returns B=1 if the operation was successful, B=0 otherwise.

        See also: NSD_BASE/LOCK NSD_BASE/UNLOCK NSD_BASE/LOCKFILENAME'''
        b=1
        if self.__lockfid__:
            try:
                self.__lockfid__.close()
                os.remove(self.lockfilename(dirname))
                self.__lockfid__ = []
            except:
                b=0
        return b
            
            
  
