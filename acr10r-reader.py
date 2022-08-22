#!/usr/bin/python3

import os
import sys
import signal
import termios
import time
import socket
import fcntl
import errno
import struct


# external files/classes
import modbus
import settings

# Temp-Humi Sensoren THGR810
sensorData = {}
humStatusTable = ["Dry", "Comfort", "Normal", "Wet"]

exitProgram = False
serialPort = None
oldSettings = None


def current_sec_time():
    return int(round(time.time()))


def current_milli_time():
    return int(round(time.time() * 1000))


def signal_handler(_signal, frame):
    global exitProgram

    print('You pressed Ctrl+C!')
    exitProgram = True


def initAnykey():
    global oldSettings

    oldSettings = termios.tcgetattr(sys.stdin)
    newSettings = termios.tcgetattr(sys.stdin)
    # newSettings[3] = newSettings[3] & ~(termios.ECHO | termios.ICANON) # lflags
    newSettings[3] = newSettings[3] & ~(termios.ECHO | termios.ICANON)  # lflags
    newSettings[6][termios.VMIN] = 0  # cc
    newSettings[6][termios.VTIME] = 0  # cc
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, newSettings)


def restoreAnykey():
    global oldSettings
    if oldSettings:
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, oldSettings)
        print("Old terminal settings restored")


def printHelp():
    print()
    print('ACR10R reader/terminal program')
    print()
    print('ESC or Ctrl-C: Exit program')
    print('1-Send request to ACR10R for data including power')
    print('2-Send request to ACR10R for data without power')
    print('h-Print this help')
    print()
    print('IP: %s PORT: %s' % (settings.tcpipServerAddress[0], settings.tcpipServerAddress[1]))
    print()


def printHexString(_str):
    for char in _str:
        print("%02X " % (ord(char)), end='')
    print()


def printHexByteString(_str):
    for v in _str:
        print("%02X " % v, end='')
    print()
    print(" msg length: %d" % len(_str))


def sendModbusMsg(sendMsg, modBusAddr):
    sendMsgList = list(sendMsg)
    sendMsgList[0] = chr(modBusAddr)
    # print(sendMsgList)
    print("modBusAddr=%d" % modBusAddr, end='')
    print(" -> send request to ACR10R: ", end='')
    sendMsg = ''
    for element in sendMsgList:
        # print("%02X " % ord(element), end='')
        sendMsg += element
    # printHexString(sendMsg)
    request = sendMsg + modbus.calculateCRC(sendMsg)
    printHexString(request)

    for char in request:
        sendByte = ord(char)
        # print("%02X " % sendByte, end='')
        sock.send(bytes([sendByte]), 1)
    # sock.send(request.encode('ascii'))


###
# Initalisation ####
###

# Init signal handler, because otherwise Ctrl-C does not work
signal.signal(signal.SIGINT, signal_handler)

# Make the following devices accessable for user
# os.system("sudo chmod 666 %s" % settings.serialPortDevice)

# Give Home Assistant and Mosquitto the time to startup
time.sleep(2)

masterMsgWithPower = "\x05\x03\x00\xF3\x00\x26"  # 0x35, 0xA7]
masterMsgWithoutPower = "\x05\x03\x00\xF2\x00\x13"  # 0xA4, 0x70]

sendCrLf = False
initAnykey()

# Create a TCP/IP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# Bind the socket to the port
sock.connect(settings.tcpipServerAddress)
fcntl.fcntl(sock, fcntl.F_SETFL, os.O_NONBLOCK)

powerCntAdd = 0
powerAvgAdd = 0
printHelp()

try:
    while not exitProgram:
        ch = os.read(sys.stdin.fileno(), 1)
        if ch != b'':
            # Key is pressed
            if ch == b'\x1b':
                print("Escape pressed: Exit")
                exitProgram = True
            elif ch == b'r':
                print("Reset powerAvg")
                powerCntAdd = 0
                powerAvgAdd = 0
            elif ch == b'1':
                sendDelayTimer = 0
                sendModbusMsg(masterMsgWithPower, 0x05)
            elif ch == b'2':
                sendDelayTimer = 0
                sendModbusMsg(masterMsgWithoutPower, 0x05)
            elif ch == b'h':
                printHelp()
            # else:
            #     print("%02X " % (ord(ch)), end='')
            #     sock.send(ch)
            #     sendCrLf = True
        else:
            if sendCrLf:
                sendCrLf = False
                print()

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
                    exitProgram = True
            else:
                msgLen = len(recvMsg)
                # print("msgLen: %d" % msgLen)
                # printHexByteString(recvMsg)
                if msgLen == 8:
                    pass  # Ignore msg
                #     # Register get request from Storion to ACR10
                    # print(" 8: ", end='')
                    # for x in recvMsg:
                    #     print("%02X " % x, end='')
                    # print()
                #     print(" msg length: %d" % len(recvMsg))
                elif msgLen == 21:
                    pass  # Ignore msg
                else:
                    # Answer from ACR10
                    if msgLen == 81:
                        print("81", end='')
                        power = True
                    elif msgLen == 89:
                        recvMsg = recvMsg[8:]
                        print("89", end='')
                        power = True
                    elif msgLen == 43:
                        print("43", end='')
                        power = False
                    elif msgLen == 51:
                        print("51", end='')
                        recvMsg = recvMsg[8:]
                        power = False
                    else:
                        print("%2d" % msgLen, end='')
                        for x in recvMsg:
                            print("%02X " % x, end='')
                        modbus.checkRecvMsgCRC(recvMsg, True)
                        print("Unknown msg")
                        continue
                    if not modbus.checkRecvMsgCRC(recvMsg, True):
                        continue
                    # for x in recvMsg:
                    #     print("%02X " % x, end='')
                    # print(" msg length: %d" % len(recvMsg))

                    #            3     5     7      9     11   13    15    17    19    21      23           27          31          35
                    # 05 03 4C+09 5D 09 3F 09 0E+10 1D 0F D9 0F F3 00 0C 00 13 00 09+13 88+00.00.00.86 00.00.00.FF 00.00.00.1C 00.00.01.A2+FF FF FF 01 FF FF FE BF FF FF FF 20 FF FF FC DD+00 00 01 2B 00 00 01 D0 00 00 00 E2 00 00 03 DB+01 C9 02 29 00 82 01 A9+E0 9B
                    # Ad-Cm-??+--Uan---Ubn--Ucn-+--Uab---Ubc--Uca-+--Ia----Ib----Ic-+--Hz-+-----------------Actief vermogen---------------+-------------------Reactief vermogen-----------+-------------------Blind vermogen--------------+---Vermogensfactor-----+-CRC-

                    if not power:
                        # 0+1: Addr+Function
                        # 2  : ????????????????????
                        # 243:3+4: 2 bytes: Uan
                        i = 3
                        i += 2
                        val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        print("Ua: %.1f V " % (float(val) / 10), end='')
                        # 244:5+6: 2 bytes: Ubn
                        i += 2
                        val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        print("Ub: %.1f V " % (float(val) / 10), end='')
                        # 245:7+8: 2 bytes: Ucn
                        i += 2
                        val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        print("Uc: %.1f V " % (float(val) / 10), end='')

                        print()

                        # # 246:9+10: 2 bytes: Uab
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Uab: %.1f V " % (float(val)/10), end='')
                        # # 247:11+12: 2 bytes: Ubc
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Ubc: %.1f V " % (float(val)/10), end='')
                        # # 248:13+14: 2 bytes: Uca
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Uca: %.1f V " % (float(val)/10), end='')

                        # # 249:15+16: 2 bytes: Ia
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Ia: %.3f A " % (float(val)/1000), end='')
                        # # 250:17+18: 2 bytes: Ib
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Ib: %.3f A " % (float(val)/1000), end='')
                        # # 251:19+20: 2 bytes: Ic
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Ic: %.3f A " % (float(val)/1000), end='')

                        # # 252:21+22: 2 bytes: Hz
                        # i += 2
                        # val = struct.unpack(">h", recvMsg[i:i + 2])[0]
                        # print("Freq: %.2f Hz " % (float(val)/100))
                    else:
                        # 253-254:23+24+25+26: 4 bytes: Pa
                        i = 23
                        val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                        print("Pa: %3dW  " % val, end='')
                        # 255-256:27+28+29+30: 4 bytes: Pb
                        i = 27
                        val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                        print("Pb: %3dW  " % val, end='')
                        # 257-258:31+32+33+34: 4 bytes: Pc
                        i = 31
                        val = struct.unpack(">i", recvMsg[i:i + 4])[0]
                        print("Pc: %3dW  " % val, end='')

                        # 259-260:35+36+37+38: 4 bytes: Ptot
                        i = 35
                        powerTotal = struct.unpack(">i", recvMsg[i:i + 4])[0]
                        print("Ptot: %4dW  " % powerTotal, end='')

                        powerAvgAdd += powerTotal
                        powerCntAdd += 1
                        powerAvg = int(powerAvgAdd / powerCntAdd)
                        powerAvgDiff = abs(powerAvg / 2)    # 50% of powerTotal

                        print("Pavg: %4dW" % powerAvg, end='')
                        if powerCntAdd >= 30:
                            powerCntAdd = 1
                            powerAvgAdd = powerTotal
                            powerAvg = powerTotal
                            print(" -> reset powerAvg after 30 counts")
                        # elif powerTotal > (powerAvg + powerAvgDiff):
                        #     print(" -> reset powerAvg > 25%% %d > %d + %d" % (powerTotal, powerAvg, powerAvgDiff))
                        #     powerCntAdd = 1
                        #     powerAvgAdd = powerTotal
                        #     powerAvg = powerTotal
                        # elif powerTotal < (powerAvg - powerAvgDiff):
                        #     print(" -> reset powerAvg < 25%% %d < %d + %d" % (powerTotal, powerAvg, powerAvgDiff))
                        #     powerCntAdd = 1
                        #     powerAvgAdd = powerTotal
                        #     powerAvg = powerTotal
                        else:
                            print()

                        # if (powerCntAdd >= 30) or (powerTotal > (powerAvg + powerAvgDiff)) or (powerTotal < (powerAvg - powerAvgDiff)):

finally:
    restoreAnykey()

print("Clean exit!")
