#!/usr/bin/python3
# -*- coding: utf-8 -*-


import os
import signal
import time
import serial
import _thread
import traceback
import json
import paho.mqtt.publish as mqtt_publish
import paho.mqtt.client as mqtt_client
import socket
import fcntl
import errno
import struct

# external files/classes
import logger
import serviceReport
import settings
import modbus

oldTimeout = 0
exitThread = False


def current_sec_time():
    return int(round(time.time()))


def current_milli_time():
    return int(round(time.time() * 1000))


def signal_handler(_signal, frame):
    global exitThread

    print('You pressed Ctrl+C!')
    exitThread = True


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("MQTT Client connected successfully")
        # client.subscribe([(settings.MQTT_TOPIC_OUT, 1), (settings.MQTT_TOPIC_CHECK, 1)])
        client.subscribe([(settings.MQTT_TOPIC_CHECK, 1)])
    else:
        print(("ERROR: MQTT Client connected with result code %s " % str(rc)))


# The callback for when a PUBLISH message is received from the server
def on_message(_client, userdata, msg):
    print(('ERROR: Received ' + msg.topic + ' in on_message function' + str(msg.payload)))


def communicationThread():
    global oldTimeout
    global exitThread

    oldTimeout = current_sec_time()
    powerCntAdd = 1000
    powerAvgAdd = 0
    powerAvgSend = 0

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Bind the socket to the port
    sock.connect(settings.tcpipServerAddress)
    # fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)

    while True:
        try:
            recvMsg = sock.recv(100)
        except Exception as e:
            err = e.args[0]
            if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                time.sleep(0.1)
                # print('No data available')
                continue
            else:
                # a "real" error occurred
                print(e)
                exitThread = True
        else:
            try:
                msgLen = len(recvMsg)
                # print("Received msgLen: %d msg: " % msgLen) #, end='')
                if msgLen == 8:
                    pass    # Ignore msg
                #     # Register get request from Storion to ACR10
                    # print(" 8: ", end='')
                elif msgLen == 21:
                    pass    # Ignore msg
                else:
                    #  Check the ACR10R Rx timeout
                    if (current_sec_time() - oldTimeout) > 300:
                        # Reset the RFLink Rx timeout timer
                        oldTimeout = current_sec_time()

                        # Report failure to Home Logic system check
                        serviceReport.sendFailureToHomeLogic(serviceReport.ACTION_RESTART, 'ACR10R receive timeout (5 min no data received)!')

                    # Answer from ACR10
                    oldTimeout = current_sec_time()
                    if msgLen == 89:
                        recvMsg = recvMsg[8:]
                        # print("89", end='')
                    elif msgLen == 81:
                        pass # Process the message normally
                        # print("81", end='')
                    elif msgLen == 57:
                        # This message is only used by Storion T10 after unit is installed, sort of testmodus
                        pass # Process the message normally
                        # print("57", end='')
                    else:
                        # Unknown message: Ignore
                        # print("Unknown msgLength (msgLen=%d): " % msgLen, end='')
                        continue

                    # Check the received msg CRC
                    if not modbus.checkRecvMsgCRC(recvMsg):
                        continue

                    sensorData = {}

                    # for x in recvMsg:
                    #     print("%02X " % x, end='')
                    # print(" msg length: %d" % len(recvMsg))
                    # Message format:
                    # 05 03 4C+09 5D 09 3F 09 0E+10 1D 0F D9 0F F3 00 0C 00 13 00 09+13 88+00 00 00 86 00 00 00 FF 00 00 00 1C 00 00 01 A2+FF FF FF 01 FF FF FE BF FF FF FF 20 FF FF FC DD+00 00 01 2B 00 00 01 D0 00 00 00 E2 00 00 03 DB+01 C9 02 29 00 82 01 A9+E0 9B
                    # Ad-Cm-??+--Uan---Ubn--Ucn-+--Uab---Ubc--Uca-+--Ia----Ib----Ic-+--Hz-+-----------------Actief vermogen---------------+-------------------Reactief vermogen-----------+-------------------Blind vermogen--------------+---Vermogensfactor-----+-CRC-

                    # # 0+1: Addr+Function
                    # # 2  : ????????????????????
                    # # 243:3+4: 2 bytes: Uan
                    # i = 3
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Ua: %.1f Volt" % (float(val)/10))
                    # # 244:5+6: 2 bytes: Ubn
                    # i = 5
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Ub: %.1f Volt" % (float(val)/10))
                    # # 245:7+8: 2 bytes: Ucn
                    # i = 7
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Uc: %.1f Volt" % (float(val)/10))

                    # # 246:9+10: 2 bytes: Uab
                    # i = 9
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Uab: %.1f Volt" % (float(val)/10))
                    # # 247:11+12: 2 bytes: Ubc
                    # i = 11
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Ubc: %.1f Volt" % (float(val)/10))
                    # # 248:13+14: 2 bytes: Uca
                    # i = 13
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Uca: %.1f Volt" % (float(val)/10))

                    # # 249:15+16: 2 bytes: Ia
                    # i = 15
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Ia: %.3f A" % (float(val)/1000))
                    # # 250:17+18: 2 bytes: Ib
                    # i = 17
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Ib: %.3f A" % (float(val)/1000))
                    # # 251:19+20: 2 bytes: Ic
                    # i = 19
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Ic: %.3f A" % (float(val)/1000))

                    # # 252:21+22: 2 bytes: Hz
                    # i = 21
                    # val = struct.unpack(">h", recvMsg[i:i+2])[0]
                    # print("Freq: %.2f Hz" % (float(val)/100))

                    # 253-254:23+24+25+26: 4 bytes: Pa
                    # i = 23
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # # print("Pa:    " % val, end='')
                    # sensorData['Pa'] = val

                    # # 255-256:27+28+29+30: 4 bytes: Pb
                    # i = 27
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # # print("Pb: %3dW  " % val, end='')
                    # sensorData['Pb'] = val

                    # # 257-258:31+32+33+34: 4 bytes: Pc
                    # i = 31
                    # val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # # print("Pc: %3dW  " % val, end='')
                    # sensorData['Pc'] = val

                    # 259-260:35+36+37+38: 4 bytes: Ptot
                    i = 35
                    powerTotal = struct.unpack(">i", recvMsg[i:i + 4])[0]
                    # print("Ptot: %4dW  " % powerTotal, end='')
                    sensorData['Ptot'] = powerTotal
                    powerAvgAdd += powerTotal
                    powerCntAdd += 1
                    powerAvg = powerAvgAdd / powerCntAdd
                    powerAvgDiff = abs(powerAvg / 2)    # 25% of powerTotal
                    # print("powerAvgDiff: %d" % powerAvgDiff)
                    if (powerCntAdd >= 7) or (powerTotal > (powerAvg + powerAvgDiff)) or (powerTotal < (powerAvg - powerAvgDiff)):
                        powerAvgSend = powerAvg
                        powerCntAdd = 1
                        powerAvgAdd = powerTotal
                        powerAvg = powerTotal
                        sendPower = True
                    else:
                        sendPower = False

                    # print("Pavg: %4dW" % powerAvg, end='')
                    sensorData['Pavg'] = int(powerAvgSend)

                    # if powerCntAdd >= 30:
                    #     print(" -> reset powerAvg after 30 counts")
                    # elif powerTotal > (powerAvg + powerAvgDiff):
                    #     print(" -> reset powerAvg (> 20%)")
                    # elif powerTotal < (powerAvg - powerAvgDiff):
                    #     print(" -> reset powerAvg (< 20%)")
                    # else:
                    #     print()

                    # msgLen = len(recvMsg)
                    # while i < (msgLen - 2):
                    #     # Process all data in msg - 4: addr,cmnd and 2xbyte CRC
                    #     valStr = recvMsg[i:i+2]
                    #     # print(valStr)
                    #     val = struct.unpack("<h", valStr)[0]
                    #     # print("%s: %d" % (valStr, val))
                    #     i += 2

                    if sendPower:
                        mqttTopic = "huis/ACR10R/ACR10R-power-meter/power"
                        mqtt_publish.single(mqttTopic, json.dumps(sensorData, separators=(', ', ':')), hostname=settings.MQTT_ServerIP, retain=True)

                    serviceReport.systemWatchTimer = current_sec_time()

            # In case the message contains unusual data
            except ValueError as arg:
                print(arg)
                traceback.print_exc()
                time.sleep(1)

            # Quit the program by Ctrl-C
            except KeyboardInterrupt:
                print("Program aborted by Ctrl-C")
                exit()

            # Handle other exceptions and print the error
            except Exception as arg:
                print("%s" % str(arg))
                traceback.print_exc()
                time.sleep(10)


def print_time(delay):
    count = 0
    while count < 5:
        time.sleep(delay)
        count += 1
        print("%s" % (time.ctime(time.time())))


###
# Initalisation ####
###
logger.initLogger(settings.LOG_FILENAME)

# Init signal handler, because otherwise Ctrl-C does not work
signal.signal(signal.SIGINT, signal_handler)

# Make the following devices accessable for user
# os.system("sudo chmod 666 %s" % settings.serialPortDevice)

# Give Home Assistant and Mosquitto the time to startup
time.sleep(2)

# First start the MQTT client
client = mqtt_client.Client()
# client.message_callback_add(settings.MQTT_TOPIC_OUT,       on_message_homelogic)
client.message_callback_add(settings.MQTT_TOPIC_CHECK,     serviceReport.on_message_check)
client.on_connect = on_connect
client.on_message = on_message
client.connect(settings.MQTT_ServerIP, settings.MQTT_ServerPort, 60)
client.loop_start()

# Create the serialPortThread
try:
    # thread.start_new_thread( print_time, (60, ) )
    _thread.start_new_thread(communicationThread, ())
except Exception:
    print("Error: unable to start the communicationThread")


# Blocking call that processes network traffic, dispatches callbacks and
# handles reconnecting.
# Other loop*() functions are available that give a threaded interface and a
# manual interface.


while not exitThread:
    time.sleep(1)  # 60s

# if serialPort is not None:
#     print('Closed serial port')

print("Clean exit!")
