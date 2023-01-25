#!/usr/bin/env python3
# ftd2_qy15.py
# coding: utf-8
import os
import sys
import json
import ctypes
import argparse


"""
Consts
"""
c_ver = 'v1.4.0'
dll_file = 'ftd2xx64.dll'
SETTINGS_JSON = 'settings.json'
PREVIOUS_PARAM = 'prev_param'
DEV_SERIAL_NO = -1
DWORD = ctypes.c_ulong

BIN_SWITCH_1 = 1
BIN_SWITCH_2 = 2
BIN_SWITCH_3 = 4
BIN_SWITCH_4 = 8


def get_args():
    global c_ver
    ps = argparse.ArgumentParser(prog='ftd2_qy15',description='ftd2_qy15 '+ c_ver)

    ps.add_argument('--sw1', action='store_true', help='Switch 1 : On, Not specified: off')
    ps.add_argument('--sw2', action='store_true', help='Switch 2 : On, Not specified: off')
    ps.add_argument('--sw3', action='store_true', help='Switch 3 : On, Not specified: off')
    ps.add_argument('--sw4', action='store_true', help='Switch 4 : On, Not specified: off')
    ps.add_argument('-r', '--reset', action='store_true', help='Ignore Previous SW params')
    ps.add_argument('-v', '--version', action='version', version='%(prog)s '+c_ver)
    ps.add_argument('--debug', action='store_true', help=argparse.SUPPRESS)

    return ps.parse_args()


def readPreviousParam(args, args_dir):
    ret = 0

    if (args.reset is not False) and (os.path.exists(os.path.join(args_dir, PREVIOUS_PARAM))):
        with open(os.path.join(args_dir, PREVIOUS_PARAM), mode='r', encoding='utf-8') as f:
            try:
                data = f.readline()
                ret = int(data)
            except:
                ret = 0

    return ret


def switch_param(args, args_dir):
    ret = 0

    p_sw_param = readPreviousParam(args, args_dir)

    if args.sw1:
        ret = ret + BIN_SWITCH_1
    if args.sw2:
        ret = ret + BIN_SWITCH_2
    if args.sw3:
        ret = ret + BIN_SWITCH_3
    if args.sw4:
        ret = ret + BIN_SWITCH_4

    # If arg is not specified, sw param setting is all off.
    if 0 == ret:
        p_sw_param = 0

    ret = p_sw_param | ret

    if args.debug:
        dbg = ['off'] * 4
        if 0 != (ret & BIN_SWITCH_1):
            dbg[0] = 'on'
        if 0 != (ret & BIN_SWITCH_2):
            dbg[1] = 'on'
        if 0 != (ret & BIN_SWITCH_3):
            dbg[2] = 'on'
        if 0 != (ret & BIN_SWITCH_4):
            dbg[3] = 'on'
        print('Switch Status : [1:{0}] [2:{1}] [3:{2}] [4:{3}]'.format(dbg[0], dbg[1], dbg[2], dbg[3]))

    with open(os.path.join(args_dir, PREVIOUS_PARAM), mode='w', encoding='utf-8') as f:
        try:
            f.write(str(ret))
        except:
            pass

    return ret


def write_byte(dll, hndl, byte):
    data = ctypes.c_byte(byte)
    written = ctypes.c_ulong(0)
    return dll.FT_Write(hndl, ctypes.pointer(data), 1, ctypes.pointer(written))


def chk_dev(args, dll):
    devNum = DWORD()
    # 0x80000000: FT_LIST_NUMBER_ONLY
    ftStatus = dll.FT_ListDevices(ctypes.pointer(devNum), None, DWORD(0x80000000))

    if 0 != ftStatus:
        print('FT_ListDevices(FT_LIST_NUMBER_ONLY) Error: {0}'.format(ftStatus))
        sys.exit()

    if args.debug:
        print('Detected devices: {0}'.format(devNum.value))

    if 0 == devNum.value:
        print('No device')
        sys.exit()

    devSerial = DWORD()
    for iNum in range(devNum.value):
        # 0x40000000|0x01: FT_LIST_BY_INDEX|FT_OPEN_BY_SERIAL_NUMBER
        ftStatus = dll.FT_ListDevices(iNum, ctypes.pointer(devSerial), DWORD(0x40000000|0x01))

        if args.debug:
            print('The serial number of device {0} is {1}'.format(iNum, devSerial.value))

        if 0 == ftStatus and devSerial.value == DEV_SERIAL_NO:
            return iNum

    print('Target device did not detected.')
    sys.exit()


def import_json(args_dir):
    global SETTINGS_JSON
    global DEV_SERIAL_NO

    # if getattr(sys, 'frozen', False):
    #     # convert to exe
    #     p_dir = os.path.dirname(os.path.abspath(sys.executable))
    # else:
    #     # not convert
    #     p_dir = os.path.dirname(os.path.abspath(__file__))

    if(os.path.exists(os.path.join(args_dir, SETTINGS_JSON))):
        json_open = open(os.path.join(args_dir, SETTINGS_JSON), 'r')
        json_load = json.load(json_open)
        if(json_load.get('serial') is not None):
            DEV_SERIAL_NO = int(json_load['serial'])


def main():
    args = get_args()

    if getattr(sys, 'frozen', False):
        # convert to exe
        p_dir = os.path.dirname(os.path.abspath(sys.executable))
    else:
        # not convert
        p_dir = os.path.dirname(os.path.abspath(__file__))

    swp = switch_param(args, p_dir)
    import_json(p_dir)

    try:
        dll_ftd2xx64 = ctypes.CDLL(dll_file)
    except OSError:
        if args.debug:
            print("The specified module was not found.")
        sys.exit()

    hdle = ctypes.c_void_p()
    ret = dll_ftd2xx64.FT_Open(chk_dev(args, dll_ftd2xx64), ctypes.pointer(hdle))
    if 0 != ret:
        print('Device Open Error: {0}'.format(ret))
        sys.exit()
#    ret = dll.FT_OpenEx("USB Serial Port", FT_OPEN_BY_SERIAL_NUMBER, ctypes.pointer(hdle))
    ret = dll_ftd2xx64.FT_SetBaudRate(hdle, 9600)  # 9600 bps
    ret = dll_ftd2xx64.FT_SetBitMode(hdle, 0xFF, 1)  # All output and bit bang mode
    ret = write_byte(dll_ftd2xx64, hdle, swp)
    ret = dll_ftd2xx64.FT_Close(hdle)


if __name__ == "__main__":
    main()
