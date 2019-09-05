#
#! coding:utf-8

import xml.etree.ElementTree as ET
from xml.etree import ElementTree
import base64
import binascii
import numpy as np
import matplotlib.pyplot as plt

SubType = {'1':'ASD','2':'CSD','3':'COH'}

class DttXMLSpectrum():
    def __init__(self,child):
        self.Name = child.attrib["Name"]
        self._getAttribute(child)
        self._getStream(child)
        
    def _getAttribute(self,child):
        self.dt       = child.find("./Param[@Name='dt']").text
        self.t0       = child.find("./Time[@Type='GPS']").text        
        self.BW       = child.find("./Param[@Name='BW']").text
        self.f0       = child.find("./Param[@Name='f0']").text
        self.df       = child.find("./Param[@Name='df']").text
        self.N        = int(child.find("./Param[@Name='N']").text)
        self.Window   = child.find("./Param[@Name='Window']").text
        self.AveType  = child.find("./Param[@Name='AverageType']").text
        self.Averages = child.find("./Param[@Name='Averages']").text        
        self.Flag     = child.find("./Param[@Name='Flag']").text
        self.Subtype  = SubType[child.find("./Param[@Name='Subtype']").text]
        self.M        = int(child.find("./Param[@Name='M']").text)
        self.dim      = child.find('./Array/Dim').text
        channel = child.findall("./Param[@Unit='channel']")
        self.Channel  = list(map(lambda x:{x.attrib['Name']:x.text},channel))
        Channel = self.Channel[0]
        for c in self.Channel:
            Channel.update(c)           
        self.Channel = Channel
        
    def _getStream(self,child):
        stream_str = child.find('./Array/Stream').text
        stream_bin = binascii.a2b_base64(stream_str)                   
        if self.Subtype == 'ASD': # float : asd           
            self.spectrum = np.frombuffer(stream_bin, dtype=np.float32)
            self.f        = np.arange(len(self.spectrum))*float(self.df)
        elif self.Subtype == 'CSD': # floatcomplex : cross spectrum
            self.spectrum = np.frombuffer(stream_bin, dtype=np.float32)
            real = self.spectrum[0::2]
            real = real.reshape(self.M,self.N)
            imag = self.spectrum[1::2]
            imag = imag.reshape(self.M,self.N)
            imag = 1j*imag
            c = real+imag
            #print c[0,:5]
            # Cxy
            # x:ChannelA
            # y:ChannelB[0-]
            self.csd = np.absolute(c)
            self.deg = np.rad2deg(np.angle(c))            
            self.f        = np.arange(len(self.csd[0]))*float(self.df)
        elif self.Subtype == '???': # float : coherence?
            self.spectrum = np.frombuffer(stream_bin, dtype=np.float32)
            self.f        = np.arange(len(self.spectrum))*float(self.df)
            #print len(self.spectrum),len(self.f)


class DttData():
    def __init__(self,xmlname):       
        tree = ElementTree.parse(xmlname)
        root = tree.getroot()
        self.spect = [DttXMLSpectrum(child) for child in root.findall("./LIGO_LW[@Type='Spectrum']")]
        pass

    def getAllSpectrumName(self):
        for s in self.spect:
            print(s.Name,s.Subtype,s.Channel['ChannelA'])

    def getASDInfo(self,chname,ref=False):
        asd = filter(lambda x:x.Subtype=="ASD", self.spect)
        asd = filter(lambda x:x.Channel['ChannelA']==chname, asd)
        print(asd[0].Averages)
    def getASD(self,chname,ref=False):
        asd = filter(lambda x:x.Subtype=="ASD", self.spect)
        asd = filter(lambda x:x.Channel['ChannelA']==chname, asd)
        asdlist = asd
        for asd in asdlist:
            #print asd.Name,asd.Subtype
            if ref==False:
                if 'Result' in asd.Name:
                    return asd.f,asd.spectrum
            elif ref==True:
                if 'Reference' in asd.Name:
                    return asd.f,asd.spectrum
            else:
                print('!')
                return None

    def getResultNum(self,chname,ref=False):
        asd = list(filter(lambda x:x.Subtype=="ASD", self.spect))
        asd = list(filter(lambda x:x.Channel['ChannelA']==chname, asd))
        num = asd[0].Name
        return int(num.split('[')[1][0])
    
    def getCSD(self,chnameA,chnameB,ref=False,**kwargs):
        import re        
        csd = list(filter(lambda x:x.Subtype=="CSD", self.spect))
        csd = list(filter(lambda x:x.Channel['ChannelA']==chnameA, csd))
        if not ref:
            csd = list(filter(lambda x: 'Reference' not in x.Name , csd))
            
        numA = self.getResultNum(chnameA,**kwargs)
            
        for c in csd[0].Channel.keys():
            if csd[0].Channel[c] == chnameB:
                num = int(c[:-1].split('[')[1])
                if num >= numA:
                    num = num -1
                elif num < numA:
                    num = num
                #print numA,num,csd[0].Channel[c]
        return csd[0].f,csd[0].csd[num],csd[0].deg[num]
    

    def getCoherence(self,chnameA,chnameB,**kwargs):        
        f = None
        f,CSD_AB,deg = self.getCSD(chnameA,chnameB)
        f,ASD_A = self.getASD(chnameA)
        f,ASD_B = self.getASD(chnameB)
        mag = (CSD_AB/(ASD_A*ASD_B))**2
        return f,mag,deg

    def getTF(self,chnameA,chnameB):        
        f = None
        f,CSD_AB,deg = self.getCSD(chnameA,chnameB)
        f,ASD_A = self.getASD(chnameA)
        f,ASD_B = self.getASD(chnameB)
        mag = CSD_AB/(ASD_A*ASD_A)
        return f,mag,deg    

