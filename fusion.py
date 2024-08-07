from OOP_ptz import ptzCamera
from OOP_MRR import TiMRRSensor
import vlc, cv2

myCam = ptzCamera('192.168.1.64', 'admin', 'a_123456')

# vlc player can be moved to ptzCamera Obj methods or __init__ method: 
player = vlc.Instance()
media_player = player.media_player_new()
rtspURL = 'rtsp://admin:a_123456@192.168.1.64:554' #+ '/Streaming/Channels/101?transportmode=unicast&profile=Profile_1'
media = player.media_new(rtspURL)
media.get_mrl()
media_player.set_media(media)

if __name__ == '__main__':

    media_player.play()

    # One of the following commands can move camera based on what is desired:

    # myCam.relative_move_command(pan=30, tilt=0, zoom=0, duration = 100000)
    # myCam.move_to_preset(myCam.preSet["John"])
    # myCam.go_to_position(pan=0, tilt=0, zoom=1)

    pan, tilt, zoom = myCam.get_position()
    print(f'pan: {pan} | tilt: {tilt} | zoom: {zoom}')