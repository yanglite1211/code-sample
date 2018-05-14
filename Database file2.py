#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import shutil
import numpy as np
import time
import re
from nsd_dbleaf import nsd_dbleaf
from nsd_pickdbleaf import *
import sys
sys.path.insert(0, '../../vhlab_toolbox_python/datastructures')
sys.path.insert(0, '../../vhlab_toolbox_python/fileio/structUtility')
from emptystruct import *
from loadStructArray import *
from saveStructArray import *
from structmerge import *

class nsd_dbleaf_branch(nsd_dbleaf):
    ''' NSD_DBLEAF_BRANCH - A class that manages branches of NSD_DBLEAF objects with searchable metadata'''
    def __init__(self, path='', name='', classnames=[], isflat=0, memory=0):
        ''' NSD_DBLEAF_BRANCH - Create a database branch of objects with searchable metadata
        
        DBBRANCH = NSD_DBLEAF_BRANCH(PATH, NAME, CLASSNAMES, [ISFLAT], [MEMORY])
        
        Creates an NSD_DBLEAF_BRANCH object that operates at the path PATH, has the
        string name NAME, and may consist of elements of classes that are found
        in CLASSNAMES. NAME may be any string. The optional argument ISFLAT is a 0/1
        value that indicates whether NSD_DBLEAF_BRANCH objects can be added as elements to
        DBBRANCH. The optional argument MEMORY is a 0/1 value that indicates whether this
        this NSD_DBLEAF_BRANCH object should only store its objects in memory (1) or write objects
        to disk as they are added (1).

        One may also use the form:

        DBBRANCH = NSD_DBLEAF_BRANCH(PARENT_BRANCH, NAME, CLASSNAMES, [ISFLAT], [MEMORY])

        where PARENT_BRANCH is a NSD_DBLEAF_BRANCH, and PATH will be taken from that
        object's directory name (that is, PARENT_BRANCH.DIRNAME() ). The new object
        will be added to the parent branch PARENT_BRANCH.

        Another variation is:

        DBBRANCH = NSD_DBLEAF_BRANCH(FILENAME, 'OpenFile'), which will read in the object
        from a filename. To developers: all NSD_DBLEAF descendents must offer this constructor.
        DBBRANCHs are containers for NSD_DBLEAF elements.'''
        
        self._path_=''  #String path; where NSD_DBLEAF_BRANCH should store its files
        self._classnames_=classnames # Cell array of classes that may be stored in the branch
        self._isflat_=isflat # 0/1 Is this a flat branch (that is, with no subbranches allowed?)
        self._memory_=memory # 0/1 Should this NSD_DBLEAF_BRANCH exist in memory rather than writing files to disk?
        self.__mdmemory__=[] # metadata in memory (if memory==1)
        self.__leaf__=[] # cell array of leafs (leaves) if local memory is storage (that is, memory==1)
        loadfromfile = 0
        parent = []
        if isinstance(path,nsd_dbleaf):
            parent = path
            parent._classnames_=[parent._classnames_[2:-2]]
            path=parent.dirname()
            if parent._isflat_:
                raise Exception('Cannot add subbranch to flat branch. '+ parent._name_+ ' is a flat branch.')
        if name and not classnames and not parent:
            if name.lower()!='openfile':
                raise Exception('Unknown command: ' +name+ '.')
            name=''
            loadfromfile = 1
        super().__init__(name)
        if loadfromfile:
            fullfilename = path
            self.readobjectfile(fullfilename)
            return
        if os.path.isdir(path) or not path:
            self._path_=path
        else:
            raise Exception('path does not exist.')
        if parent:
            potential_existing_nsd_dbleaf_branch_obj = parent.load('_name_',self._name_)[0];
            if not potential_existing_nsd_dbleaf_branch_obj:
                parent.add(self)
            else:
                if potential_existing_nsd_dbleaf_branch_obj._isflat_ != self._isflat_ or potential_existing_nsd_dbleaf_branch_obj._memory_ != int(self._memory_) :
                    raise Exception('nsd_dbleaf_branch with name '+ self._name_+ ' already exists with different isflat or memory parameters.')
                self=potential_existing_nsd_dbleaf_branch_obj
        
    def metadata(self):
        '''METADATA - Return the metadata from an NSD_DBLEAF_BRANCH'''
        if not self._path_:
            md=self.__mdmemory__
        else:
            if os.path.isfile(self.metadatafilename()):
                md=loadStructArray(self.metadatafilename())
            else:
                md=[]
        return md
    
    def metadatastruct(self):
        ''' METADATASTRUCT - return the metadata fields and values for an NSD_DBLEAF_BRANCH
         Returns the metadata fieldnames and values for NSD_DBLEAF_BRANCH_OBJ.
         This is simply MDS = struct('is_nsd_dbleaf_branch',1,'name',NAME,'objectfilename',OBJECTFILENAME);'''
        mds=super(nsd_dbleaf_branch,self).metadatastruct()
        mds.update({'is_nsd_dbleaf_branch' : 1})
        return mds
    
    def add(self,newobj):
        ''' ADD - Add an item to an NSD_DBLEAF_BRANCH
         Adds the item NEWOBJ to the NSD_DBLEAF_BRANCH NSD_DBLEAF_BRANCH_OBJ.  The metadata of the branch
         is updated and the object is written to the subdirectory of NSD_DBLEAF_BRANCH_OBJ.
         NEWOBJ must be a descendent of type NSD_DBLEAF.
         A branch may not have more than one NSD_DBLEAF with the same 'name' field.'''
        if not isinstance(newobj,nsd_dbleaf):
            raise Exception('objects to be added must be descended from NSD_DBLEAF.')
        
        if self._isflat_ and isinstance(newobj,nsd_dbleaf_branch):
            raise Exception('The NSD_DBLEAF_BRANCH ' +self._name_ +' is flat; one cannot add branches to it.')
            
        match = 0
        for i in range(len(self._classnames_)):
            match=isinstance(newobj,eval(self._classnames_[i]))
            if match:
                break
        if not match:
            raise Exception('The object of class ' +type(newobj).__name__+ ' does not match any of the allowed classes for the NSD_DBLEAF_BRANCH.')
        
        # have to check for unique names in this branch
        [indexes,md] = self.search('_name_', newobj._name_)
        if indexes:
            raise Exception('NSD_DBLEAF with name '+ newobj._name_+ ' already exists in the NSD_DBLEAF_BRANCH ' +self._name_+ '. Names must be unique within a branch.')
        
        omd = newobj.metadatastruct()
        # now have to reconcile possibly different metadata structures
        fn1=list(dict.keys(md[0]))
        fn2=list(dict.keys(omd))
        if not md[0]:
           md[0]=omd 
        else:
            if fn1!=fn2:
                for j in range(len(md)):
                    newmd={**md[j],**omd}
                    for i in newmd:
                        if i not in md[j]:
                            md[j].update({i:''})
                        if i not in omd:
                            omd.update({i:''})
            md.append(omd)
                
        # now deal with saving metadata and the object
        if int(self._memory_):
            self.__mdmemory__=md
            self.__leaf__.append(newobj)
        else:
            #write the object to our unique subdirectory
            newobj.writeobjectfile(self.dirname())
            #now write md back to disk
            self.writeobjectfile([],0,md)
            
    def remove(self,objectfilename):
       '''REMOVE - Remove an item from an NSD_DBLEAF_BRANCH
       Removes the object with the object file name equal to OBJECTFILENAME from NSD_DBLEAF_BRANCH_OBJ.'''
       b=self.lock()
       if not b:
           raise Exception('Tried to lock metadata but the file was in use! Error! Delete ' +self.lockfilename(self._path_) +' if a program was interrupted while writing metadata.')
       [index,md]=self.search('_objectfilename_',objectfilename)
       if not index:
           self.unlock()
           raise Exception('No such object '+ objectfilename +'.')
       tokeep=list(set(range(len(md))).symmetric_difference(set(index)))
       md=list(np.array(md)[tokeep])
       
       if int(self._memory_):#update memory
          self.__mdmemory__=md
          self.__leaf__=self.__leaf__(tokeep)
       else:
           # update the file
           self.writeobjectfile(self._path_,1,md)
           # delete the leaf from disk
           theleaf=nsd_pickdbleaf(self.dirname()+'/'+objectfilename)
           theleaf.deleteobjectfile(self.dirname())  
       self.unlock()
    
    def update(self,nsd_dbleaf_obj):
        '''UPDATE - update the contents of a NSD_DBLEAF object that is stored in an NSD_DBLEAF_BRANCH
        Update the record of an NSD_DBLEAF object that is already stored in a NSD_DBLEAF_BRANCH'''
        
        #need to lock
        b=self.lock()
        if not b:
            raise Exception('Could not obtain lock on object '+ self._objectfilename_ +'.')
        [index,md] = self.search('_objectfilename_', nsd_dbleaf_obj._objectfilename_)
        if not index:
            self.unlock()
            raise Exception('The object to be updated is not in this branch: ' +nsd_dbleaf_obj._objectfilename_+' is not in '+ self._objectfilename_+ '.')
        # we assume that metadata field identities haven't changed
        omd=metadatastruct(nsd_dbleaf_obj)
        md[index] = structmerge(md[index],omd)
        if int(self._memory_):
            self.__mdmemory__ = md
            self.__leaf__[index]=nsd_dbleaf_obj
        else:
            # write the object to our unique subdirectory
            nsd_dbleaf_obj.writeobjectfile(self.dirname(),1)
            # now write md back to disk
            self.writeobjectfile([],1,md)
        self.unlock()
             
    def search(self, *varargin):
        ''' SEARCH - search for a match in NSD_DBLEAF_BRANCH metadata
         Searches the metadata parameters PARAM1, PARAM2, and so on, for 
         value1, value2, and so on. If valueN is a string, then a regular expression
         is evaluated to determine the match. If valueN is not a string, then the
         the items must match exactly.'''
        md=self.metadata()
        if not md:
            return [],[{}]
        indexes = []
        for i in range(0,2,len(varargin)):
            for j in md:
                if not varargin[i] in list(j.keys()):
                    raise Exception(varargin[i] +' is not a field of the metadata.')
                if varargin[i+1]==j.get(varargin[i]):
                    indexes.append(md.index(j))
            else:
                matches_here='dont know how to write'
            indexes=list(set(indexes))
            return indexes,md
        
    def load(self,*varargin):
        ''' LOAD - Load an object(s) from an NSD_DBLEAF_BRANCH
         Returns the object(s) in the NSD_DBLEAF_BRANCH NSD_DBLEAF_BRANCH_OBJ at index(es) INDEXES or
         searches for an object whose metadata parameters PARAMS1, PARAMS2, and so on, match
         VALUE1, VALUE2, and so on (see NSD_DBLEAF_BRANCH/SEARCH).
         If more than one object is requested, then OBJ will be a cell list of matching objects.
         Otherwise, the object will be a single element. If there are no matches, empty ([]) is returned.'''
        md=[]
        if len(varargin)>=2:
            [indexes, md] = self.search(*varargin)
        else:
            indexes=varargin[0]
            
        if indexes:
            if not md:
                md = self.metadata()
            obj=[]
            for i in range(len(indexes)):
                if self._path_:
                    obj.append(nsd_pickdbleaf(self.dirname()+'/'+md[indexes[i]].get('_objectfilename_')))
                else:
                    obj.append(self.__leaf__(indexes[i]))
            
        else:
            obj=[None]
        return obj
    
    def numitems(self):
        '''NUMITEMS - Number of items in this level of an NSD_DBLEAF_BRANCH
        Returns the number of items in the NSD_DBLEAF_BRANCH object.'''
        md=self.metadata()
        n=len(md)
        return n
    
    def writeobjectfile(self,thedirname=[], locked=0, metad=1):
        '''WRITEOBJECTFILE - write the object data to the disk
        Writes the object data of NSD_DBLEAF_BRANCH object NSD_DBLEAF_BRANCH_OBJ to disk.'''
        if not thedirname:
            if int(self._memory_):
                raise Exception('This branch '+ self._name_ +' has no path. THEDIRNAME must be provided.')
            thedirname=self._path_
        if metad==1:
            metad=self.metadata()
        b=1
        # now we have to proceed in 4 steps
        # a) obtain the lock so we know nobody else is going to be writing our files
        # b) write our metadata 
        # c) if we are in memory only, write our leafs
        # d) write our own object data
        
        # semaphore
        if not locked:
            b=self.lock(thedirname)
        if not b:
            raise Exception('Tried to write metadata but the file was in use! Error! Delete ' +self.lockfilename(thedirname) +' if a program was interrupted while writing metadata.')
        if metad:
            saveStructArray(self.metadatafilename(),metad)
        else:
            if os.path.isfile(self.metadatafilename()):
                os.remove(self.metadatafilename())
        # now, if in memory, write leaf objects
        if int(self._memory_):
            # remove our subdirectory, it is guaranteed to exist after .dirname() runs
            shutil.rmtree(self.dirname(thedirname))
            for i in range(leng(self.__leaf__)):
                self.__leaf__(i).writeobjectfile(self.dirname(thedirname))
        # now write our object data
        super(nsd_dbleaf_branch,self).writeobjectfile(thedirname,1)
        if not locked:
            b=self.unlock(thedirname)
            if not b:
                raise Exception('yikes! could not remove lock!')
                
    def stringdatatosave(self):
        '''STRINGDATATOSAVE - Returns a set of strings to write to file to save object information
        Return a cell array of strings to save to the objectfilename'''
        [data,fieldnames]=super(nsd_dbleaf_branch,self).stringdatatosave()
        data.append(str(self._memory_))
        fieldnames.append('$memory')
        data.append(str(self._classnames_))
        fieldnames.append('$classnames')
        return data,fieldnames
    
    def setproperties(self, properties, values):
        ''' SETPROPERTIES - set the properties of an NSD_DBLEAF_BRANCH object
         Given a cell array of string PROPERTIES and a cell array of the corresponding
         VALUES, sets the fields in NSD_DBLEAF_BRANCH_OBJ and returns the result in OBJ.
         If any entries in PROPERTIES are not properties of NSD_DBLEAF_BRANCH_OBJ, then
         that property is skipped.
         the properties that are actually set are returned in PROPERTIESSET.'''
        fn=list(self.__dict__.keys())
        reg=re.compile(r'_\w+_')
        fn=list(filter(reg.match,fn))
        obj=self
        properties_set=[]
        for i in range(len(properties)):
            if properties[i].startswith('$'):
                properties[i]='_'+properties[i][1:]+'_'
        for i in range(len(properties)):
            if properties[i] in fn:
               exec('self.'+properties[i]+'="'+values[i]+'"')
               properties_set.append(properties[i])
        ind=np.where(np.array(properties)=='path')[0]
        if ind:
            subdirname = obj.dirname()
            subobjs = load(obj,'_name_','(.*)')
            for j in range(len(subobjs)):
                if isinstance(subobjs[j],nsd_dbleaf_branch):
                    subobjs[j]=subobjs[j].setproperties('path',subdirname)
                    obj=obj.update(subobjs[j])
        return [obj,properties_set]
    
    def readobjectfile(self,fname):
        '''Reads the NSD_DBLEAF_BRANCH_OBJ from the file FNAME (full path).'''
        obj=super(nsd_dbleaf_branch,self).readobjectfile(fname)
        [obj._path_,filename]=os.path.split(fname)
        # now, if in memory only, we need to read in the metadata and leafs
        if int(obj._memory_):
            [parent,myfile]=os.path.split(fname)
            obj.__mdmemory__=loadStructArray(obj.metadatafilename(parent))
            obj.__leaf__=[]
            for i in range(len(obj.__mdmemory__)):
                obj.__leaf__[i]=self.readobjectfile(obj.dirname(parent) +'/'+ obj.__mdmemory__[i].get('_objectfilename_'))
    
    def lock(self,thedirname=''):
       ''' LOCK - lock the metadata file and object files so other processes cannot change them
        Attempts to obtain the lock on the metadata file nad object files. If it is successful,
        B is 1. Otherwise, B is 0.
        THEDIRNAME is the directory where the lock file resides. If it is not provided, then 
        NSD_DBLEAF_BRANCH_OBJ.path is used.'''
       b=0
       if not thedirname:
           thedirname=self._path_
       if int(self._memory_):
           number_of_tries = 30
           mytry = 0
           while self.__lockfid__ and mytry<number_of_tries:
               time.sleep(1)
               mytry+=1
           if not self.__lockfid__:
               self.__lockfid__='locked'
               b=1
       else:
           b=super(nsd_dbleaf_branch,self).lock(thedirname)
       return b
    
    def unlock(self,thedirname=''):
        '''UNLOCK - unlock the metadata file and object files so other processes can change them
        Removes the lock file from the NSD_DBLEAF_BRANCH NSD_DBLEAF_BRANCH_OBJ.'''
        b=1
        if not thedirname:
           thedirname=self._path_
        if self.__lockfid__:
            if self.__mdmemory__:
                self.__lockfid__=[]
            else:
                b=super(nsd_dbleaf_branch,self).unlock(thedirname)
        return b
    
    def metadatafilename(self,usethispath=''):
        '''FILENAME - Return the (full path) metadata database file name associated with an NSD_DBLEAF_BRANCH
        Returns the filename of the metadata of an NSD_DBLEAF_BRANCH object (full path).'''
        if not int(self._memory_):
            usethispath=self._path_
        fname=usethispath+'/'+self._objectfilename_+'.metadata.dbleaf_branch.nsd'
        return fname
    
    def dirname(self,usethispath=''):
        ''' DIRNAME - Return the (full path) database directory name where objects are stored
         Returns the directory name of the items of an NSD_DBLEAF_BRANCH object (full path).'''
        if not int(self._memory_):
            usethispath=self._path_
        elif not usethispath:
            return ''
        dname=usethispath+'/'+self._objectfilename_+'.subdir.dbleaf_branch.nsd'
        if not os.path.isdir(dname):
            os.mkdir(dname)
        return dname
    
    def deleteobjectfile(self,thedirname=''):
        ''' DELETEOBJECTFILE - Delete / remove the object file (or files) for NSD_DBLEAF_BRANCH
         Delete all files associated with NSD_DBLEAF_BRANCH_OBJ in directory THEDIRNAME (full path).'''
        if not thedirname and int(self._memory_):
            raise Exception('This branch is in memory only, so to delete any files we need to know which directory it may be stored in.')
        elif not thedirname:
            thedirname=self._path_
        b=1
        try:
            os.remove(self.metadatafilename())
        except:
            b=0
        shutil.rmtree(self.dirname(thedirname))
        b=super(nsd_dbleaf_branch,self).deleteobjectfile(thedirname)
        return b