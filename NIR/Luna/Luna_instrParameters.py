import wx
from Luna_instr import Luna
import LaserPanel_Luna

class Luna_instrParameters(wx.Panel):
    name='LUNA: Optical Vector Analyzer'
    def __init__(self, parent, connectPanel, **kwargs):
        super(Luna_instrParameters, self).__init__(parent)
        self.connectPanel = connectPanel
        self.visaAddrLst = kwargs['visaAddrLst']
        self.iplst = '192.168.2.11','192.168.2.1'
        self.port='80'
        self.InitUI()
        
        
    def InitUI(self):
        sb = wx.StaticBox(self, label='Luna Parameters');
        vbox = wx.StaticBoxSizer(sb, wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        self.para1 = wx.BoxSizer(wx.HORIZONTAL)
        self.para1name = wx.StaticText(self,label='Luna PC IP adress')
        self.para1tc = wx.TextCtrl(self,value='192.168.2.11')
        self.para1.AddMany([(self.para1name,1,wx.EXPAND|wx.ALIGN_LEFT),(self.para1tc,1,wx.EXPAND|wx.ALIGN_RIGHT)])
        
        self.para2 = wx.BoxSizer(wx.HORIZONTAL)
        self.para2name = wx.StaticText(self,label='Port number')
        self.para2tc = wx.TextCtrl(self,value='80')
        self.para2.AddMany([(self.para2name,1,wx.EXPAND|wx.ALIGN_LEFT),(self.para2tc,1,wx.EXPAND|wx.ALIGN_RIGHT)])
        
        
        self.disconnectBtn = wx.Button(self, label='Disconnect')
        self.disconnectBtn.Bind( wx.EVT_BUTTON, self.disconnect)
        self.disconnectBtn.Disable()
        
        self.connectBtn = wx.Button(self, label='Connect')
        self.connectBtn.Bind( wx.EVT_BUTTON, self.connect)
        
        hbox.AddMany([(self.disconnectBtn, 0, wx.ALIGN_RIGHT), (self.connectBtn, 0, wx.ALIGN_RIGHT)])
        
        vbox.AddMany([(self.para1,0,wx.EXPAND), (self.para2,0,wx.EXPAND), (hbox, 0, wx.ALIGN_BOTTOM)])
     
        self.SetSizer(vbox)
        
    def connect(self, event):
        self.laser = Luna();
        self.laser.connect(self.para1tc.GetValue(),self.para2tc.GetValue(), reset=0, forceTrans=1)
        self.laser.panelClass = LaserPanel_Luna.laserTopPanel # Give the laser its panel class
        self.connectPanel.instList.append(self.laser)
        self.disconnectBtn.Enable()
        self.connectBtn.Disable()
     
        
    def disconnect(self, event):
        self.laser.disconnect()
        if self.laser in self.connectPanel.instList:
            self.connectPanel.instList.remove(self.laser)
        self.disconnectBtn.Disable()
        self.connectBtn.Enable()
         