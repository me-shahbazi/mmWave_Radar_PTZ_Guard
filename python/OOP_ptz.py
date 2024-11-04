# This program developed to control PTZcamera using ISAPI in python.
# ISAPI refers to Internet Server Application Programming Interface mostly
# used in HikVision devices.
# Sending HTTP request and XML commands are the basis of the program.
import requests
from requests.auth import HTTPDigestAuth
import re
import vlc

# This Object defined for handeling HikVision camera modules
class ptzCamera():
    
    # Some General variables for calling pre-defined preSets in camera:
    preSet = {}

    # This patern will be used for extracting desiered information from responses:
    statusPatern = r"<[absoluteZoom,azimuth,elevation]+>\d+</[absoluteZoom,azimuth,elevation]+>"

    def __init__(self, camera_ip, username, password):
        self.camera_ip = camera_ip
        self.username = username
        self.password = password

        self.player = vlc.Instance()
        self.media_player = self.player.media_player_new()
        rtspURL = f'rtsp://{username}:{password}@{camera_ip}:554'
        media = self.player.media_new(rtspURL)
        self.media_player.set_media(media)

    def relative_move_command(self, pan, tilt, zoom, duration = 500):
        # duration is the time in milliseconds for which the command is executed
        # pan, tilt, zoom in this function refers to the speed of the camera movement
        PTZ_CONTROL_URL = f'http://{self.camera_ip}/ISAPI/PTZCtrl/channels/1/Momentary'
        xml_payload = f'''  <PTZData>
                            <pan>{pan}</pan>
                            <tilt>{tilt}</tilt>
                            <zoom>{zoom}</zoom>
                            <Momentary>
                                <duration>{duration}</duration>
                            </Momentary>
                        </PTZData>'''
        
        response = requests.put(PTZ_CONTROL_URL, auth=HTTPDigestAuth(username=self.username, password=self.password), data=xml_payload)

        if response.status_code == 200:
            print('PTZ command sent successfully')
        else:
            print(f'Failed to send PTZ command: {response.status_code}')

    def move_to_preset(self, PRESET):
        try:
            # PreSet positions has been defined previously in Camera Settings.
            # PreSet values most be some integers refering to one of those defined positions.
            PreSet_URL = f'http://{self.camera_ip}/ISAPI/PTZCtrl/channels/1/presets/{PRESET}/goto'
            xml_payload = f'<PTZData><PresetID>{PRESET}</PresetID></PTZData>'

            response = requests.put(PreSet_URL, auth=HTTPDigestAuth(self.username, self.password), data=xml_payload, headers={'Content-Type': 'application/xml'})

            # if response.status_code == 200:
            #     print('Moved to preset successfully')
            # else:
            #     print(f'Failed to move to preset: {response.status_code}')
        except requests.exceptions.NameError:
            print('Failed to move to preset')

    def go_to_position(self, pan, tilt, zoom):
    # Absolute Move
    # This function moves the camera into the position specified by pan, tilt and zoom
        GoToURL = f'http://{self.camera_ip}/ISAPI/PTZCtrl/channels/1/absolute'
        xml_payload = f'''<PTZData>
                            <AbsoluteHigh>
                                <elevation>{10*tilt}</elevation>
                                <azimuth>{10*pan}</azimuth>
                                <absoluteZoom>{zoom}</absoluteZoom>
                            </AbsoluteHigh>
                        </PTZData>'''
        # <AbsoluteHigh><!--high-accuracy positioning which is accurate to one decimal place-->

        response = requests.put(GoToURL, auth=HTTPDigestAuth(self.username, self.password), data=xml_payload)
        if response.status_code == 200:
            print('Moved to PTZ successfully')
        else:
            print(f'Failed to move to PTZ: {response.status_code}')

    def get_position(self) -> tuple[int, int, int]:
    # This function returns current position of PTZcamera object
        StatusURL = f'http://{self.camera_ip}/ISAPI/PTZCtrl/channels/1/status'
        response = requests.get(StatusURL, auth=HTTPDigestAuth(self.username, self.password))
        
        if response.status_code == 200:
            print('Status recived successfully')
            # statusPatern = r"<[absoluteZoom,azimuth,elevation]+>\d+</[absoluteZoom,azimuth,elevation]+>"
            # self.statusPatern is the regex str defined at the begging of the object declartion on top
            # based on trial and error and analysing the response value in this function.
            ptzData = re.findall(self.statusPatern, response.text)
            # print(ptzData)
            
            self.tilt_position = int(re.findall(r"\d+", ptzData[0])[0])//10 # ptzData[0] : elevation
            self.pan_position  = int(re.findall(r"\d+", ptzData[1])[0])//10 # ptzData[1] : azimuth        
            self.zoom_position = int(re.findall(r"\d+", ptzData[2])[0])//10 # ptzData[2] : absoluteZoom
        else:
            print(f'Failed to move to PTZ: {response.status_code}')

        return self.pan_position, self.tilt_position, self.zoom_position
    
    def play_stream(self):
        self.media_player.play()
    
    def close_stream(self):
        self.media_player.stop()
        self.media_player.release()
        self.player.release()

if __name__ == '__main__':
    
    myCam = ptzCamera('192.168.1.64', 'admin', 'a_123456')

    myCam.preSet = {"HIKZERO" : 1, 
                    "DefaultView" : 2, 
                    "MySelf" : 3, 
                    "ALLZERO" : 4,
                    "DrRoom" : 5,
                    "MainEntrance" : 6,
                    "BackDoor" : 7}
    
    # One of the following commands can move camera based on what is desired:
    
    # myCam.relative_move_command(pan=30, tilt=0, zoom=0, duration = 1000)
    myCam.move_to_preset(myCam.preSet["MainEntrance"])
    # myCam.go_to_position(pan=300, tilt=20, zoom=1)

    pan, tilt, zoom = myCam.get_position()
    print(f'pan: {pan} | tilt: {tilt} | zoom: {zoom}')