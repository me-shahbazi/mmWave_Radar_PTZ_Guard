# This Program developed in order to provide easy access to Ti Radar Sensor
# import needed libraries:
import serial, struct, time
import threading
import serial.tools.list_ports as ports_list
import cv2
import numpy as np

# Define Medium Range Radar Sensor object to be used in a OOP:
class TiMRRSensor():
    # Statics essential for decoding data packets
    magicWord    = b'\x02\x01\x04\x03\x06\x05\x08\x07'
    magicWordLen = len(magicWord)
    
    MsgHeader_format_str = "IIIIIIII"
    MsgHeader_size = struct.calcsize(MsgHeader_format_str)
    MsgHeader_attributes = [
                "version", "totalPacketLen", "platform", "frameNumber",
                "timeCpuCycles", "numDetectedObj", "numTLVs", "subFrameNumber"
            ]
    
    TLattributes = ["type", "length"]
    TLformat = "II"
    TLformatSize = struct.calcsize(TLformat)
    #____________________________________________
    # Length of Different TLV types: (Bytes)
    Tracker_Struct_Bytes = 12
    OBJ_Struct_Bytes     = 10
    Cluster_Struct_Bytes = 8
    #____________________________________________
    # Different Colors for simpler tracking visualisation
    Colors = [(255,0,0), (0,255,0), (0,0,255), (255,255,0), (255,0,255), (0, 255, 255), (150,200,50), (0,150,200), (150,0,250), (250,150,250)]
    #____________________________________________
    # Srounding Field of View Initial declaration used in UI.
    fovInitFlag = True
    frontRange_ = 25   # 150 -> 25
    widthRange_ = 25 # chose as always frontRange_ > widthRange_ # 40*2 -> 10*2
    everyMeterPixels = int(1080//frontRange_)
    fiveMetersPixels  = int(5 * everyMeterPixels)
    #____________________________________________
    # TrackerID.
    ObjectsArray = np.zeros((1,12))
    
    def deFOV(self): # define field of View
        if self.fovInitFlag:
            # Simple and Clear Checked Field
            
            # maximum range of MRR output meters [user guide] = 150
            # maximum range pixels = 150*(1080//150) = 1050
            # pixels of every meter = 1080//150 = 7
            
            # frontRange_ = 150
            # widthRange_ = 40*2
            # everyMeterPixels = 1080//frontRange_
            
            length = self.everyMeterPixels * (self.frontRange_)
            width  = self.everyMeterPixels * (self.widthRange_)
            self.img = np.ones((length, width, 3), dtype= np.uint8) * 255 # *255: white screen pixels
            # every 10 meter: self.tenMetersPixels
            for i in range(int(width/self.fiveMetersPixels)):
                self.img[:,self.fiveMetersPixels*i] = (0, 0, 0) 
            for j in range(int(length/self.fiveMetersPixels)):
                self.img[self.fiveMetersPixels*j,:] = (0, 0, 0)
            self.img[:,int(width//2)] = (0,0,255)
            self.fovInitFlag = False # Just runs once
        else:
            # Static Objects added to the field of View (gray ones)
            # learnedImg defines in the __init__ method as returning value of Learn method
            self.img = self.learnedImg.copy()
    
    def __init__(self):
        # Methods and functions in below run at the begining of defining a new MRR Obj
        # Like as soon as : myRadar = TiMRRSensor()
        self.Connect()
        self.deFOV()
        self.learnedImg = self.Learn(500)
        self.dispFlag = True
        self.parseFlag = True

    def Connect(self):
        # This Methods is used for connecting to the USB device
        print('Searching for ports...')
        ports = list(ports_list.comports())
        for p in ports:
            print('Found port:', p)
            if 'XDS110 Class Auxiliary Data Port' in str(p):
                Dataport = str(p)[:4]
            elif 'XDS110 Class Application/User UART' in str(p):
                CLIport = str(p)[:4]
        self.DataReceiver = serial.Serial(port= Dataport, baudrate=921600, timeout=5) # Auxiliary Data Port
        self.CliHandle    = serial.Serial(port= CLIport , baudrate=115200, timeout=1) # Command Line Interface Handle
        print('Ports connected successfully.')

    def closeConnection(self):
        # This Methods is used for disconnecting from the USB device
        # And also for safe closing UI with out any malfunctioning

        # By Turning off this flags parallel threads will be ended safely
        self.dispFlag = False
        self.parseFlag = False
        time.sleep(0.2)

        # Close USB Connection
        self.DataReceiver.close()
        try:
            self.CliHandle.write(('sensorStop\n').encode('utf-8'))

            for _ in range(4):
                if response := self.CliHandle.readline().decode('utf-8').strip():
                    print("AWR1843: ", response)
                else:
                    # print("No response received.")
                    break
        finally:
            self.CliHandle.close()
            print("*************************")
            print("Developed by @me-shahbazi")

    def Configure(self, CFGaddress):
        # This function doesn't work in MRR because there is no configuration
        with open(CFGaddress, 'r') as cfgFile:
            print("\nConfiguring RADAR Sensor...")
            for command in cfgFile:
                if not command.startswith('%'):
                    time.sleep(0.5)
                    print('\n' + command.strip())
                    self.CliHandle.write((command.strip() + '\n').encode('utf-8')) # Command sent to the AWR1843
                    
                    counter = 0
                    while True:
                        response = self.CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                        print("AWR1843: " , response)
                        counter += 1

                        if 'Error' in response:
                            afterError = self.CliHandle.readline().decode('utf-8').strip() # Geting Response from it
                            print("AWR1843: " , afterError)
                            break

                        if counter > 5:
                            print('!!! Something went wrong !!!')
                            break

                        if 'Done' in response: # O.K.
                            print("OK!")
                            break
                            
                    if 'Error' in response:
                        break
    
    def Learn(self, repeat):
        # in this stage MRR detects clutters with speed = 0.
        # before main program starts it locates the steady clutters
        self.LearnModeFlag = True
        for _ in range(repeat): # repeat : number of initial frames to learn clustters
            self.parseOne()
        self.LearnModeFlag = False
        return self.img.copy() # Gray Squares will fix on FOV (field of view)

    def parseWhile(self):
        # This method will keep parsing recived data as long as self.parseFlag is True
        while self.parseFlag:
            self.parseOne()

    def parseOne(self):     
        data = self.DataReceiver.read(self.magicWordLen)
        if data == self.magicWord:
            # print("self.ObjectsArray:\n", self.ObjectsArray)
            print("\t\t\t\t\t----------------------------")
            print("\t\t\t\t\t\t*** New Message: ***")


            bMsgHeader = self.DataReceiver.read(self.MsgHeader_size)
            tup = struct.unpack(self.MsgHeader_format_str, bMsgHeader)

            msgHeader = {
                attribute: tup[i]
                for i, attribute in enumerate(self.MsgHeader_attributes)
            }
            msgHeader["version"]  = hex(msgHeader["version"])[2:]
            msgHeader["platform"] = hex(msgHeader["platform"])[2:]
            print("Msg Header:\n   ", msgHeader)

            MsgBody = self.DataReceiver.read(msgHeader["totalPacketLen"]-(self.magicWordLen + self.MsgHeader_size)) 

            MsgPointer = 0

            for _ in range(msgHeader["numTLVs"]):
                bTL = MsgBody[MsgPointer : MsgPointer + self.TLformatSize]
                MsgPointer += self.TLformatSize
                tup = struct.unpack(self.TLformat, bTL)
                TLheader = {
                    attribute: tup[i]
                    for i, attribute in enumerate(self.TLattributes)
                }
                print("--------------------------------")
                print("TLV type: ", TLheader["type"])
                print("TLV length: ", TLheader["length"])
                
                if TLheader["type"] == 1: # Get detected object descriptor
                    self.getObj(MsgBody[MsgPointer : MsgPointer + TLheader["length"]])
                elif TLheader["type"] == 2: # Clusters
                    self.getCluster(MsgBody[MsgPointer : MsgPointer + TLheader["length"]])
                elif TLheader["type"] == 3: # Tracker
                    self.getTracker(MsgBody[MsgPointer : MsgPointer + TLheader["length"]], msgHeader["frameNumber"])
                elif TLheader["type"] == 4: # Parking Assist
                    pass
                else: 
                    print("Undifined TLV")
                
                MsgPointer += TLheader["length"]

            self.ObjectsArray = self.ObjectsArray[self.ObjectsArray[:, 10] >= msgHeader["frameNumber"]-200]
            # print("msgHeader[\"frameNumber\"]-200 : ", msgHeader["frameNumber"]-200)
            # print("len(self.ObjectsArray): ",len(self.ObjectsArray))
    def getObj(self, bNQ):
        (numObj, xyzQFormat) = struct.unpack('HH', bNQ[0:4])
        invXYZQFormat = 1.0/(2**xyzQFormat)
        bNQ = bNQ[4:]

        # print("Doppler\tPeakVal\tX\tY\tZ\tRange")
        for i in range(numObj):
            tup = struct.unpack('hHhhh', bNQ[i*10:(i+1)*10])

            Doppler, PeakVal, X, Y, Z = tup
            Doppler = tup[0] * invXYZQFormat
            X =       tup[2] * invXYZQFormat
            Y =       tup[3] * invXYZQFormat
            Z =       -(tup[4] * invXYZQFormat)
            Range_ =  round(np.sqrt(X**2 + Y**2 + Z**2), 2)
            # print("%.2f\t%d\t%.2f\t%.2f\t%.2f\t%.2f" %(Doppler, PeakVal, X, Y, Z, Range_))
    
    def getCluster(self, bNC):
        (numObj, xyzQFormat) = struct.unpack('HH', bNC[0:4])
        oneByXyzQFormat = 1.0/(2**xyzQFormat)
        bNC = bNC[4:]
        
        # print("X_\tY_\txSize\tySize\tarea")
        for i in range(numObj):
            tup = struct.unpack('hhHH', bNC[i*8:(i+1)*8])

            X_      = tup[0] * oneByXyzQFormat
            Y_      = tup[1] * oneByXyzQFormat
            xSize   = tup[2] * oneByXyzQFormat
            ySize   = tup[3] * oneByXyzQFormat
            area    = xSize * ySize * 4
            # print("%.2f\t%.2f\t%.2f\t%.2f\t%.2f" %(X_, Y_, xSize, ySize, area))

    def getTracker(self, bNQ, frameNumber):
        (numObj, xyzQFormat) = struct.unpack('HH', bNQ[0:4])

        oneByXyzQFormat = 1.0/(2**xyzQFormat)
        bNQ = bNQ[4:]
        
        # Moving Object Counter:
        MOCnt = 0
        ObjID = 0

        for i in range(numObj):
            tup = struct.unpack('hhhhHH', bNQ[i*self.Tracker_Struct_Bytes:(i+1)*self.Tracker_Struct_Bytes])

            X_, Y_, VX_, VY_, xSize, ySize = tuple(element * oneByXyzQFormat for element in tup)
            # print("X_\tY_\tVX_\tVY_\txSize\tySize")
            # print("%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f" %(X_, Y_, VX_, VY_, xSize, ySize))
            Range_ = np.sqrt(X_**2 + Y_**2)
            Doppler_ = (VY_*Y_ + VX_*X_)/Range_
            Area_ = 4*xSize*ySize
            # print("\n*** *** ***\nRange_\tDoppler_")
            # print("%.2f\t%.2f\n*** *** ***\n" %(Range_, Doppler_))

            DrawRectAngle = True
            if (Doppler_ > 0.4 or Doppler_ < -0.4) and (not self.LearnModeFlag):
                MOCnt += 1
                Color = (0,0,255) if Doppler_ > 0 else (255,0,0) # approaching: blue | leaving: red
                # Color = self.Colors[MOCnt%10]
                margin = 3
                print("X_\tY_\tVX_\tVY_\txSize\tySize")
                print("%.2f\t%.2f\t%.2f\t%.2f\t%.2f\t%.2f" %(X_, Y_, VX_, VY_, xSize, ySize))
                print("\n*** *** ***\nRange_\tDoppler_\tArea_")
                print("%.2f\t%.2f\t%.2f\n*** *** ***\n" %(Range_, Doppler_, Area_))

                self.ObjectsArray = np.append(self.ObjectsArray, [[X_, Y_, VX_, VY_, xSize, ySize, Range_, Doppler_, Area_, i, frameNumber, ObjID]],axis=0)
                print("Seen frameNumber:", frameNumber)

            elif (Doppler_ < 0.0004 or Doppler_ > -0.0004) and (self.LearnModeFlag):
                Color = (120,120,120)
                margin = 7 # self.everyMeterPixels
            elif Doppler_ == 0 and (not self.LearnModeFlag):
                Color = (120,120,120)
                margin = 3 # int(self.everyMeterPixels//2)
            else:
                DrawRectAngle = False
                Color = (0,0,0)
                margin = 0

            # Display output:
            # self.img.shape[1] : width of FOV
            if X_ > self.img.shape[1]   /self.everyMeterPixels/2:
                X_ = self.img.shape[1]  /self.everyMeterPixels/2
            elif X_ < -self.img.shape[1]/self.everyMeterPixels/2:
                X_ = -self.img.shape[1] /self.everyMeterPixels/2
            
            # where does this 7 Comes from : 1080//150
            pixels = int(X_*self.everyMeterPixels+self.img.shape[1]//2) , self.img.shape[0]-int(Y_*self.everyMeterPixels)
            startPoint = pixels[0]-margin , pixels[1]-margin
            endPoint   = pixels[0]+margin , pixels[1]+margin

            if DrawRectAngle:
                self.img = cv2.rectangle(self.img, startPoint, endPoint, Color, -1)
            
    def Display(self):
        while self.dispFlag:
            cv2.imshow("Field Of View", self.img)
            time.sleep(0.055)
            pressedKey = cv2.waitKey(1) # wait for 0.06 seconds
            if pressedKey == ord("q"): break
        cv2.destroyAllWindows()
    
    def clearWatchDog(self):
        while (self.dispFlag and (not self.LearnModeFlag)):
            oldImg = self.img.copy()
            time.sleep(10) # clear the scene affter 10s stationary
            if np.array_equal(oldImg, self.img) :
                self.deFOV()

if __name__ == '__main__':
    
    myRadar = TiMRRSensor()
    

    t1 = threading.Thread(target=myRadar.parseWhile  , daemon= False)
    t2 = threading.Thread(target=myRadar.Display, daemon= True)
    t3 = threading.Thread(target=myRadar.clearWatchDog, daemon= True)

    t1.start()
    t2.start()
    t3.start()
    
    t2.join()

    myRadar.closeConnection()