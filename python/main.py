import threading
import numpy as np
import time
from OOP_ptz import ptzCamera
from OOP_MRR import TiMRRSensor

myCam = ptzCamera('192.168.1.64', 'admin', 'a_123456')
Default_flag = True
myCam.preSet = {"HIKZERO" : 1, 
                "DefaultView" : 2, 
                "MySelf" : 3, 
                "ALLZERO" : 4,
                "DrRoom" : 5,
                "MainEntrance" : 6,
                "BackDoor" : 7,
                "Lab" : 8,
                "BLE" : 9,
                "Near" : 10,
                "BLDr" : 11,
                "Middle": 12,
                "BDrB" : 13}

globalArray  = []
globalClouds = []
myBuffer_Tracker = np.zeros(12)
myBuffer_Clouds = np.zeros(9)
# Valid_Clouds = np.zeros(9)
myRadar = TiMRRSensor(globalArray, globalClouds)
myRadar.minSpeed = 0.2
myRadar.DisplayPointClouds = True

class State_():
    def isinEntrance(location):
        x, y = location
        return (-10 <= x <= -5.5) and (10 <= y <= 17)

    def BLE(location): # preSet : 9
        x, y = location
        return (-5.5 <= x <= -2) and (9 <= y <= 13.5)

    def isinLab(location):
        x, y = location
        return (-2 <= x <= 0) and (10.5 <= y <= 13)

    def BLDr(location): # preSet : 11
        x, y = location
        return (0 <= x <= 2.5) and (10 <= y <= 14)

    def isinDrRoom(location):
        x, y = location
        return (2.5 <= x <= 4.5) and (10 <= y <= 16)

    def BDrB(location): # preSet : 13
        x, y = location
        return (4.5 <= x <= 6.5) and (9 <= y <= 14)

    def isinBackDoor(location):
        x, y = location
        return (6.5 <= x <= 12) and (9 <= y <= 14)

    def NearView(location): # preSet : 10
        x, y = location
        return (-4 <= x <= 3) and (2 <= y <= 7)

    def Middle(location): # preSet : 12
        x, y = location
        return (-4 <= x <= 4.5) and (7 <= y <= 10)

def moveOrder(target):
    # Implement your own logic to move the camera based on the received target position
    location = (target[0], target[1])

    if State_.NearView(location):
        myCam.move_to_preset(myCam.preSet["Near"])
        return "Near"
    
    elif State_.Middle(location):
        myCam.move_to_preset(myCam.preSet["Middle"])
        return "Middle"

    elif State_.BDrB(location):
        myCam.move_to_preset(myCam.preSet["BDrB"])
        return "BDrB"
    
    elif State_.isinBackDoor(location):
        myCam.move_to_preset(myCam.preSet["BackDoor"])
        return "BackDoor"
    
    elif State_.isinDrRoom(location):
        myCam.move_to_preset(myCam.preSet["DrRoom"])
        return "DrRoom"
    
    elif State_.BLDr(location):
        myCam.move_to_preset(myCam.preSet["BLDr"])
        return "BLDr"
    
    elif State_.BLE(location):
        myCam.move_to_preset(myCam.preSet["BLE"])
        return "BLE"
    
    elif State_.isinLab(location):
        myCam.move_to_preset(myCam.preSet["Lab"])
        return "Lab"
    
    elif State_.isinEntrance(location):
        myCam.move_to_preset(myCam.preSet["MainEntrance"])
        return "MainEntrance"
    
    else:
        pass
        
    return False

def Track():
    global globalArray
    global myBuffer_Tracker
    global myBuffer_Clouds
    global Default_flag
    lastOBJ_time  = time.time()
    result = False
    
    while True:
        time.sleep(.02)

        # -- Tracker Process:
        if (len(globalArray) > 0) and not (myBuffer_Tracker[-1] == globalArray[0][-1]).all():
            myBuffer_Tracker = np.array(globalArray[0])

            result = moveOrder(myBuffer_Tracker[-1])
            
            lastOBJ_time = time.time()
            Default_flag = True
        # -- Point Clouds Process:
        if (len(globalClouds) > 0) and not (myBuffer_Clouds[-1] == globalClouds[0][-1]).all():
            myBuffer_Clouds = np.array(globalClouds[0])
            
            countNearMRRcloud = 0
            countNearUSRRcloud = 0
            countEntranceMRRcloud = 0
            countDrRoomMRRcloud = 0
            
            for i in range(len(myBuffer_Clouds)):
                if (myBuffer_Clouds[i][8] == 0 and myBuffer_Clouds[i][5] > 4300) or (myBuffer_Clouds[i][8] == 1 and myBuffer_Clouds[i][5] > 2800):
                # myBuffer_Clouds[i][8] : SubFrame Type (0: MRR , 1: USRR)
                # myBuffer_Clouds[i][5] : PeakValue
                    if (3 >myBuffer_Clouds[i][0] > -4) and (myBuffer_Clouds[i][1] < 7):
                        if myBuffer_Clouds[i][8] == 0:
                            countNearMRRcloud += 1
                        elif myBuffer_Clouds[i][8] == 1:
                            countNearUSRRcloud += 1
                    
                elif ( -10 < myBuffer_Clouds[i][0] < -7 ) and (myBuffer_Clouds[i][1] > 12):
                    # print(f"{round(myBuffer_Clouds[i][0],1)} ,{round(myBuffer_Clouds[i][1],1)} , {myBuffer_Clouds[i][5]}")
                    # print(countEntranceMRRcloud)
                    countEntranceMRRcloud += 1
                
                elif ( 2.5 < myBuffer_Clouds[i][0] < 4.5 ) and (15 > myBuffer_Clouds[i][1] > 12):
                    countDrRoomMRRcloud += 1
            

            if (result == False) and (countNearMRRcloud > 1 or countNearUSRRcloud > 1):  
                # print("if Confirmed MRR: %d , USRR: %d" %(countMRRcloud, countUSRRcloud))
                myCam.move_to_preset(myCam.preSet["Near"])
                result = "Near"
                lastOBJ_time = time.time()
                Default_flag = True
            
            if (result == False) and (countEntranceMRRcloud > 2):  
                myCam.move_to_preset(myCam.preSet["MainEntrance"])
                result = "MainEntrance"
                lastOBJ_time = time.time()
                Default_flag = True

            if (result == False) and (countDrRoomMRRcloud > 1):  
                myCam.move_to_preset(myCam.preSet["DrRoom"])
                result = "DrRoom"
                lastOBJ_time = time.time()
                Default_flag = True

        # -- DefaultView preSet:
        if Default_flag and ((time.time()-lastOBJ_time) > 10):
            myCam.move_to_preset(myCam.preSet["DefaultView"])
            result = False
            Default_flag = False
        
        elif (time.time()-lastOBJ_time) > 60:
            myCam.move_to_preset(myCam.preSet["DefaultView"])
            
if __name__ == '__main__':

    pan, tilt, zoom = myCam.get_position()
    print(f'pan: {pan} | tilt: {tilt} | zoom: {zoom}')
    
    myCam.move_to_preset(myCam.preSet["DefaultView"])
    
    myCam.play_stream()

    t1 = threading.Thread(target=myRadar.parseWhile  , daemon= False)
    t2 = threading.Thread(target=myRadar.Display, daemon= True)
    t3 = threading.Thread(target=myRadar.clearWatchDog, daemon= True)
    t4 = threading.Thread(target=Track, daemon=False)

    t1.start()
    t2.start()
    t3.start()
    t4.start()


    
    t2.join()
    

    myRadar.closeConnection()
    myCam.close_stream()