import time
import subprocess
import numpy as np
import os.path
from datetime import date

class Luna(object):
    name = 'Luna Optical Vector Analyzer'
    isMotor= False
    isLaser= True
    connected= False  
    scan_range=0.2 #For single wavelength scan
    filename = "output.txt"
    folder_path = r"C:/Users/mlpadmin/Desktop/IDA/NIR/Luna"
    file_location = os.path.join(folder_path, filename)
    
    def connect(self,ip, port, reset = 0, forceTrans=1, autoErrorCheck=1): 
        #Identify that you are talking to right device
        self.port=port
        self.ip=ip
        subprocess.call(['Sendcmd.exe','*IDN?',ip,port])
        connected = True
        err=subprocess.call(['Sendcmd.exe','SYST:ERR?',ip,port])
        if err==0:
            print ("Luna Optical Vector Analyzer at your service")
        else:
            print ("Something is not working")
    
    def disconnect(self):
        print ("adios amigos") 
    
    def setTLSState(self,onoff,slot):
         if onoff=='on':
             switch=1
         elif onoff=='off':
             switch=0
         subprocess.call(['SendCmd.exe','SYST:LASE {}'.format(switch),self.ip,self.port]) 
    
        
    def findDUT(self): ##Should be a more efficient way of finding DUT without scan...
        subprocess.call(['SendCmd.exe','CONF:FDUT 1',self.ip,self.port])
        self.readPWM(1,1) 
    
    def deactDUT(self):
        subprocess.call(['SendCmd.exe','CONF:FDUT 0',self.ip,self.port])
    
    def setLunaWvl(self,wavelength,scan_range):
        self.setTLSState('on',1)
        subprocess.call(['SendCmd.exe','CONF:CWL {}'.format(wavelength),self.ip,self.port])
        subprocess.call(['SendCmd.exe','CONF:RANG {}'.format(scan_range),self.ip,self.port])
        self.findDUT()
        self.deactDUT()
    
    def readPWM(self, slot, chan):  
        #simulate quick reading of the insertion loss by performing a short sweept over 0.05 nm. This needs to be done separately using setwvl
        ###########
        #####"Warning: for faster iteration during fine align, DUT length is not measured at each iteration. From manual, difference less than 0.1m is ok" 
        ##########
        
        subprocess.call(['SendCmd.exe','SCAN',self.ip,self.port])
        for i in range(0, 100):
            temp = subprocess.check_output(['Sendcmd.exe','*OPC?',self.ip,self.port])
            print(f"not ready {i}")
            if '1' in temp:
                print("ready")        
                break
            #Find av insertion loss    
        ans=subprocess.check_output(['Sendcmd.exe','FETC:MEAS? 0',self.ip,self.port])
        vec=ans.split('\r\n')
        del vec[len(vec)-4: len(vec)]
        del vec[0:3]
        #print vec
        new_list = [float(i) for i in vec]
        vec=np.array(new_list)
        
        av=np.mean(vec)
       # print av
        return av
        
    
    def sweep(self):
             
        ini_wvl=self.sweepStartWvl
        final_wvl=self.sweepStopWvl
        self.setTLSState('on',1)
        
        #Min and Max allowed values
        min_wvl=1525.0
        max_wvl=1610.79

        if ini_wvl < min_wvl:
            print("initial wavelength cannot be less than 1525. initial wavelength set to 1525.")
        if final_wvl > max_wvl:
            print("final wavelength cannot be more than 1610.79. final wavelength set to 1610.79.")        
        #values to be given to luna
        rang=final_wvl-ini_wvl
        centerwvl=ini_wvl+rang/2

        
        subprocess.call(['SendCmd.exe','CONF:CWL {}'.format(centerwvl),self.ip,self.port])
        subprocess.call(['SendCmd.exe','CONF:RANG {}'.format(rang),self.ip,self.port])
    
        actual_rang=subprocess.check_output(['Sendcmd.exe','CONF:RANG?',self.ip,self.port])
        actual_cwl=subprocess.check_output(['Sendcmd.exe','CONF:CWL?',self.ip,self.port])
#    
        print(f"center wavelength set to {actual_cwl} nm")
        print('Range set to {actual_rang} nm')
        print(f"Time domain resolution bandwidth: {subprocess.check_output(['SendCmd.exe','CONF:TWRB? {}'.format(centerwvl),self.ip,self.port])}")
        
           
        
        subprocess.call(['SendCmd.exe','CONF:FDUT 1',self.ip,self.port])
        for i in range(0, 100):
            temp = subprocess.check_output(['Sendcmd.exe','*OPC?',self.ip,self.port])
            print(f"not ready {i}")
            if '1' in temp:
                print("ready")        
                break
        subprocess.call(['SendCmd.exe','SCAN',self.ip,self.port])
        for i in range(0, 100):
            temp = subprocess.check_output(['Sendcmd.exe','*OPC?',self.ip,self.port])
            print("not ready {i}")
            if '1' in temp:
                print("ready")        
                break
     
        print(subprocess.check_output(['SendCmd.exe','SYST:ERR?',self.ip,self.port]))
        if os.path.exists(self.file_location)== True:
            now=time.strftime("%d-%b-%Y-%X",time.gmtime())
            self.file_location="{}{}_{}.txt".format(self.folder_path,self.filename,now)
        subprocess.call(['SendCmd.exe','SYST:SAVS {}'.format(self.file_location),self.ip,self.port])
        print(f"file name: {self.filename}.txt. saved at {self.file_location}") 
        print(subprocess.check_output(['SendCmd.exe','SYST:ERR?',self.ip,self.port]))
        d=np.loadtxt("{}".format(self.file_location),skiprows=9)
        Wavelength=d[:,0]
        InsertionLoss=d[:,2]
        Linphase=d[:,7]
        
        return Wavelength,InsertionLoss,Linphase