#
# Copyright 2015, Michael Caverley
#

import wx
import myMatplotlibPanel
import traceback

class tlsPanel(wx.Panel):
    """ Panel which contains controls used for controlling the laser"""

    laserNumSweepMap = dict([('1', 1), ('2', 2), ('3', 3),('4', 4), ('5', 5), ('6', 6),('7', 7), ('8',8), ('9', 9), ('10', 10)])
  
    def __init__(self, parent, laser, graphPanel):
        super(tlsPanel, self).__init__(parent)
        self.devName = 'Laser';
        self.laser = laser;
        self.graphPanel = graphPanel
        self.InitUI()   
        
    def InitUI(self):
    
        
        vboxOuter = wx.BoxSizer(wx.VERTICAL)
        
        sbCW = wx.StaticBox(self, label='CW Settings');
        vboxCW = wx.StaticBoxSizer(sbCW, wx.VERTICAL)
      
        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
                
        st1 = wx.StaticText(self, label='Laser status:')
       
        self.laserOnBtn = wx.Button(self, label='ON', size=(50, 20))
        self.laserOnBtn.Bind( wx.EVT_BUTTON, self.OnButton_LaserOn)
        
        self.laserOffBtn = wx.Button(self, label='OFF', size=(50, 20))
        self.laserOffBtn.Bind( wx.EVT_BUTTON, self.OnButton_LaserOff)
        
        hbox1.AddMany([(st1, 2, wx.EXPAND), (self.laserOffBtn, 1, wx.EXPAND), (self.laserOnBtn, 1, wx.EXPAND)])
       
        hbox4 = wx.BoxSizer(wx.HORIZONTAL)
        
        st_wavelength = wx.StaticText(self, label='Wavelength (nm)')
        
        self.tc_wavelength = wx.TextCtrl(self)
        self.tc_wavelength.SetValue('1550')
        
        self.btn_wavelength = wx.Button(self, label='Set', size=(50, 20))
        self.btn_wavelength.Bind( wx.EVT_BUTTON, self.OnButton_WavelengthSet)
        
        hbox4.AddMany([(st_wavelength, 3, wx.EXPAND), (self.tc_wavelength, 2, wx.EXPAND), (self.btn_wavelength, 1, wx.EXPAND)])
        
        vboxCW.AddMany([ (hbox1, 0, wx.EXPAND), (hbox4, 0, wx.EXPAND)]);
        ###
        sbSweep = wx.StaticBox(self, label='Sweep Settings');
        vboxSweep = wx.StaticBoxSizer(sbSweep, wx.VERTICAL)
        
        hbox5 = wx.BoxSizer(wx.HORIZONTAL)
        
        st4 = wx.StaticText(self, label='Start (nm)')
        
        self.startWvlTc = wx.TextCtrl(self)
        self.startWvlTc.SetValue('0')
        
        hbox5.AddMany([(st4, 1, wx.EXPAND), (self.startWvlTc, 1, wx.EXPAND)])
        ###
        hbox6 = wx.BoxSizer(wx.HORIZONTAL)
        st5 = wx.StaticText(self, label='Stop (nm)')
        
        self.stopWvlTc = wx.TextCtrl(self)
        self.stopWvlTc.SetValue('0')
        
        hbox6.AddMany([(st5, 1, wx.EXPAND), (self.stopWvlTc, 1, wx.EXPAND)])
        ###
        hbox7 = wx.BoxSizer(wx.HORIZONTAL)
        
        st6 = wx.StaticText(self, label='Step (nm)')
        
        self.stepWvlTc = wx.TextCtrl(self)
        self.stepWvlTc.SetValue('0')
        
        hbox7.AddMany([(st6, 1, wx.EXPAND), (self.stepWvlTc, 1, wx.EXPAND)])
        
        hbox11 = wx.BoxSizer(wx.HORIZONTAL)
        
        st9 = wx.StaticText(self, label='Number of scans')
        
        numSweepOptions = ['1', '2', '3','4','5','6','7','8','9','10']
        self.numSweepCb = wx.ComboBox(self, choices=numSweepOptions, style=wx.CB_READONLY, value='1')
        hbox11.AddMany([(st9, 1, wx.EXPAND), (self.numSweepCb, 1, wx.EXPAND)])
        
        hbox8 = wx.BoxSizer(wx.HORIZONTAL)
        
        filenameSt = wx.StaticText(self, label='filename')
        
        self.filename = wx.TextCtrl(self)
        self.filename.SetValue('filename')
        
        hbox8.AddMany([(filenameSt, 1, wx.EXPAND), (self.filename, 1, wx.EXPAND)])
        ###
        
        self.sweepBtn = wx.Button(self, label='Sweep', size=(50, 20))
        self.sweepBtn.Bind( wx.EVT_BUTTON, self.OnButton_Sweep)

        vboxSweep.AddMany([(hbox5, 0, wx.EXPAND), (hbox6, 0, wx.EXPAND), (hbox7, 0, wx.EXPAND), (hbox8, 0, wx.EXPAND),\
                             (hbox11, 0, wx.EXPAND), (self.sweepBtn, 0, wx.ALIGN_CENTER)]);
        
        vboxOuter.AddMany([(vboxCW, 0, wx.EXPAND), (vboxSweep, 0, wx.EXPAND)])
        #fgs.AddGrowableCol(0, 1)
        #hbox.Add(fgs, proportion=1, flag=wx.ALL, border=15)
        self.SetSizer(vboxOuter)
        
    
    def OnButton_LaserOn(self, event):
        self.laser.setTLSState('on', 1)
            
    def OnButton_LaserOff(self, event):
        self.laser.setTLSState('off', 1)
            
    
    def OnButton_WavelengthSet(self, event):
        #wavelength=float(self.tc_wavelength.GetValue())
#        if (wavelength < 1470) or (wavelength > 1660):
#            print 'wavelength out of allowed bound: must be between 1470 nm and 1660 nm'
#            exit
#        else:    
        self.laser.setLunaWvl(float(self.tc_wavelength.GetValue()), self.laser.scan_range )

    def copySweepSettings(self):
        """ Copies the current sweep settings in the interface to the laser object."""
       
        self.laser.sweepStartWvl = float(self.startWvlTc.GetValue());
        self.laser.sweepStopWvl = float(self.stopWvlTc.GetValue());
        self.laser.sweepStepWvl = float(self.stepWvlTc.GetValue());
        self.laser.name=str(self.filename.GetValue());
        self.laser.sweepNumScans = self.laserNumSweepMap[self.numSweepCb.GetValue()]
        
        
    def drawGraph(self, wavelength, power1,power2):
        self.graphPanel.axes.cla()
        self.graphPanel.axes.plot(wavelength,power1)
        self.graphPanel.axes.plot(wavelength,power2)        
        self.graphPanel.axes.ticklabel_format(useOffset=False)
        self.graphPanel.canvas.draw()
    
    def haltDetTimer(self):
        print 'halt'
#        timer = self.detectorPanel.timer
#        if timer.IsRunning():
#            timer.Stop()
            
    def startDetTimer(self):
        print "start"
#        timer = self.detectorPanel.timer
#        if not timer.IsRunning():
#            timer.Start()
        
    def OnButton_Sweep(self, event):
        #self.haltDetTimer()
        try:
           # wavelength1 = float(self.startWvlTc.GetValue());
            #wavelength2 = float(self.stopWvlTc.GetValue());
 
            self.copySweepSettings()
            (self.wavelengthArr,self.InsLoss,self.Linphase)=self.laser.sweep()
#            self.wavelengthArr, self.powerArr = 
#            (self.wavelengthArr,self.powerArr1,self.powerArr2)=self.laser.sweep()            
#            #self.lastSweepWavelength, self.lastSweepPower = self.laser.sweep();
            self.graphPanel.canvas.sweepResultDict = {}
            self.graphPanel.canvas.sweepResultDict['wavelength'] = self.wavelengthArr  
            self.graphPanel.canvas.sweepResultDict['Insertion Loss'] = self.InsLoss  
            self.graphPanel.canvas.sweepResultDict['Linear Phase deviation'] = self.Linphase    
            self.drawGraph(self.wavelengthArr,self.InsLoss,self.Linphase)
#            
        except Exception as e:
            print traceback.format_exc()
            print 'Huston we got an error: {}'.format(e)
            
        #self.laser.setAutorangeAll()
        #self.startDetTimer()
        

class laserTopPanel(wx.Panel):        
    def __init__(self, parent, laser, showGraph=True):
        super(laserTopPanel, self).__init__(parent)
        
        self.showGraph = showGraph
        self.laser = laser;
        self.laser.ctrlPanel = self # So the laser knows what panel is controlling it
        self.InitUI()
        
    def InitUI(self):  
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        if self.showGraph:
            self.graph = myMatplotlibPanel.myMatplotlibPanel(self)
            hbox.Add(self.graph, flag=wx.EXPAND, border=0, proportion=1)
        
        self.laserPanel = laserPanel(self, self.laser, self.graph)
    
        hbox.Add(self.laserPanel, flag=wx.LEFT | wx.TOP | wx.EXPAND, border=0, proportion=0)
        

        self.SetSizer(hbox)
        
class laserPanel(wx.Panel):
  
    def __init__(self, parent, laser, graph):
        super(laserPanel, self).__init__(parent)
        self.graphPanel = graph
        self.laser = laser;
        self.InitUI()
        
        
     
        
    def InitUI(self):  
        sb = wx.StaticBox(self, label='Laser');
        vbox = wx.StaticBoxSizer(sb, wx.VERTICAL)
        
        
        self.laserPanel = tlsPanel(self, self.laser, self.graphPanel)
    
        vbox.Add(self.laserPanel, flag=wx.LEFT | wx.TOP | wx.EXPAND, border=0, proportion=0)
        
        self.detectorPanelLst = list();
        
        #for ii in xrange(self.laser.getNumPWMChannels()):
        self.detectorPanel = detectorPanel(self, 1, self.laser)
        self.laserPanel.detectorPanel = self.detectorPanel;

        vbox.Add(self.detectorPanel, border=0, proportion=0, flag=wx.EXPAND)
    
        #sl = wx.StaticLine(self.panel);
        self.SetSizer(vbox)
        
    def OnClose(self, event):
        self.laserPanel.Destroy();
        self.detetorPanel.Destroy();
        self.Destroy();
        
class detectorPanel(wx.Panel):
  
    def __init__(self, parent, numDet, laser):
        super(detectorPanel, self).__init__(parent)
        self.numDet = numDet
        self.laser = laser
        self.InitUI()   
        
    def InitUI(self):
    
        #font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
        #font.SetPointSize(12)
        
        sbDet = wx.StaticBox(self, label='Detector Settings');
#        
        vbox = wx.StaticBoxSizer(sbDet, wx.VERTICAL)
#        hbox = wx.BoxSizer(wx.HORIZONTAL)
#        
#        self.initialRangeSt = wx.StaticText(self, label='Initial range (dBm)')
#        #self.initialRangeSt.SetFont(font)
#        hbox.Add(self.initialRangeSt, proportion=1, flag=wx.ALIGN_LEFT)
#        
#        self.initialRangeTc = wx.TextCtrl(self, size=(40,20))
#        self.initialRangeTc.SetValue('-20')
#        hbox.Add(self.initialRangeTc, proportion=0, flag=wx.EXPAND|wx.RIGHT, border=15)
#        
#        
#        self.sweepRangeDecSt = wx.StaticText(self, label='Range dec. (dBm)')
#        #self.sweepRangeDecSt.SetFont(font)
#        hbox.Add(self.sweepRangeDecSt, proportion=1, flag=wx.ALIGN_LEFT)
#        
#        self.sweepRangeDecTc = wx.TextCtrl(self, size=(40,20))
#        self.sweepRangeDecTc.SetValue('20')
#        hbox.Add(self.sweepRangeDecTc, proportion=0, flag=wx.EXPAND)
#
#        
#
#        vbox.Add(hbox, proportion=0, flag=wx.EXPAND, border=0)
#        
#        
#        sl = wx.StaticLine(self);
#        vbox.Add(sl, proportion=0, flag=wx.EXPAND)
#        
        self.detectorPanelLst = list();
#        for ii,slotInfo in zip(self.laser.pwmSlotIndex,self.laser.pwmSlotMap):
        name = 'Luna detector'
        det = individualDetPanel(self, name=name)
        self.detectorPanelLst.append(det)
        vbox.Add(det, proportion=1, flag=wx.LEFT, border=15)
        sl = wx.StaticLine(self);
        vbox.Add(sl, proportion=0, flag=wx.EXPAND)
        self.SetSizer(vbox)
        
      #  self.laser.setAutorangeAll()
        self.timer = wx.Timer(self, wx.ID_ANY)
        self.Bind(wx.EVT_TIMER, self.UpdateAutoMeasurement, self.timer)
        self.timer.Start(1000)
        
    def getActiveDetectors(self):
        activeDetectorLst = list();
        for ii,panel in enumerate(self.detectorPanelLst):
            if panel.enableSweepCb.GetValue() == True:
                activeDetectorLst.append(ii)
        return activeDetectorLst
#        
    def UpdateAutoMeasurement(self, event):
        for ii,panel in enumerate(self.detectorPanelLst):
            if panel.autoMeasurementEnabled:
                panel.PowerSt.SetLabel(str(self.laser.readPWM(panel.slot, panel.chan)))
#                
    def OnClose(self, event):
        self.timer.Stop();
        
class individualDetPanel(wx.Panel):
  
    def __init__(self, parent, name='', slot=1, chan=1):
        super(individualDetPanel, self).__init__(parent)
        self.name = name
        self.slot = slot
        self.chan = chan
        self.autoMeasurementEnabled = 0;
        self.InitUI()   
        
    def InitUI(self):
#    
#        #font = wx.SystemSettings_GetFont(wx.SYS_SYSTEM_FONT)
#        #font.SetPointSize(12)
#        
#
        hbox = wx.BoxSizer(wx.HORIZONTAL)
#        
        fgs = wx.FlexGridSizer(4, 2, 8, 25)
#        
        self.detNameSt = wx.StaticText(self, label=self.name)
        #self.detNameSt.SetFont(font)
#        
        self.autoMeasurementCb = wx.CheckBox(self, label='Auto measurement')
        #self.autoMeasurementCb.SetFont(font)
        self.autoMeasurementCb.Bind(wx.EVT_CHECKBOX, self.OnCheckAutoMeasurement);
#        
        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
#        
#
        st1 = wx.StaticText(self, label='Power (dBm):')
        #st1.SetFont(font)
        hbox2.Add(st1, proportion=0, flag=wx.ALIGN_RIGHT)
#        
#        
        self.PowerSt = wx.StaticText(self, label='-100')
#        #self.PowerSt.SetFont(font)
        hbox2.Add(self.PowerSt, proportion=0, flag=wx.ALIGN_RIGHT)
#        
#        
#        
#        self.enableSweepCb = wx.CheckBox(self, label='Include in sweep')
#        self.enableSweepCb.SetValue(False)
#        #self.enableSweepCb.SetFont(font)
#        
        fgs.AddMany([(self.detNameSt), \
                     (self.autoMeasurementCb), (hbox2, 1, wx.EXPAND)])
#        
        #fgs.AddGrowableCol(0, 1)
        hbox.Add(fgs, proportion=1, flag=wx.ALL, border=0)
        self.SetSizer(hbox)
#        
    def OnCheckAutoMeasurement(self, event):
        if self.autoMeasurementCb.GetValue():
            self.autoMeasurementEnabled = 1;
        else:
            self.autoMeasurementEnabled = 0;

