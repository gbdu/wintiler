#!/usr/bin/python3
#
# Requires: xprop, xdotool, xwininfo, wmctrl
#
#       xprop: window stack order and desktop geometry
#       xdotool: identify selected window and move mouse
#       xwininfo: window geometry information
#       wmctrl: change focus


import sys
import os
import subprocess
import re

from collections import Counter
import operator

# Config section:

scale = 16
lastchar='A' # You can use something like awesome font icons here (as
             # unicode chars that the term understands) end of config
             # section

# Globbals:

selected_char = ""
desktop_geo = None
known_symbols = {}

def get_active_window():
    cmd = ["xdotool", "getactivewindow"]

    decoded = subprocess.check_output(cmd).decode("utf-8")
    return int(decoded)

def parse_winfo(linfo):
    dinfo = {}
    for i in linfo:
        if not i: continue
        nline = i.replace(" ","")
        line = nline.replace("xwininfo:","")
        if line.startswith("Windowid"):
            ep = line.find('\"')
            if ep == -1:
                print ("ERROR, wrong value passed from xwininfo")
                return None
            else:
                wid = line[9:ep]
                title = line[ep:].replace("\"","")
                title = title.replace("\'", "")
                dinfo.update(title=title)
                dinfo.update(wid=wid)
        else:
            el = i.strip().lower()
            if el.startswith("corners"):
                corners=(el[8:].split())
                dinfo.update(corners=corners)
            else:
                el = nline
                el = el.replace("r-l", "rl")
                el = el.replace("-geometry", "mgeometry:")
                el = el.lower()
                keys = ["absoluteupperleftx", "absoluteupperlefty", \
                	"relativeupperleftx", "relativeupperlefty", \
                	"width", "height"]
                for k in keys :
                    if el.startswith(k):
                        val= el[len(k)+1:]
                        dinfo.update({k:int(val)})
    return dinfo


def get_desktop_info(xprop_output):
    x = xprop_output.find("_NET_DESKTOP_GEOMETRY(CARDINAL)")
    if x != -1 :
        xo = xprop_output[x:]
        xx = xo.find("\n")
        if xx != -1:
            ds=xprop_output[x+33:x+xx]
            ds = ds.replace(" ","")
            ds = ds.split(",")
            desktop_geo = (int(ds[0]), int(ds[1]))
            
            return desktop_geo
        else:
            print("could not find desktop dimensions")
            exit(1)

def get_client_stack(xprop_output):
    x = xprop_output.find("_NET_CLIENT_LIST_STACKING(WINDOW)")
    
    if x != -1:
        xo = xprop_output[x:]
        xx = xo.find("\n")
        if xx != -1:
            s = xprop_output[x+46:x+xx]
            return [x.strip() for x in s.split(",")]
        else:
            print("could not find windows")
            exit(1)
    
def get_window_info(win):
    cmd = ["xwininfo", "-id", "%s" % win]

    minfo = {}

    decoded = subprocess.check_output(cmd).decode("utf-8")

    winfo_as_list = decoded.split('\n')
    return parse_winfo(winfo_as_list)


def create_test_buffer(d=None):
    if not d:
        d = desktop_geo

    global scale
    #scale = 1
    w = int(d[0]/scale)
    h = int(d[1]/scale)

    print(w,h)

    buffer = [ [ '0' for x in range(h) ] for y in range(w)]
    return buffer

def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))

def populate_buffer(b,winfos):
    # b is a list of columns (which are lists of chars)
    # scan each window
    print(desktop_geo)
    for i in winfos:
        for col in range(int(i["absoluteupperleftx"]/scale),\
                         int(i["absoluteupperleftx"]/scale+i["width"]/scale)):
            for row in range(int(i["absoluteupperlefty"]/scale),\
                             int(i["absoluteupperlefty"]/scale+i["height"]/scale)):
                # print (col,row)
                try:
                    b[col][row-1] = i['char']
                except IndexError:
                    cc = clamp(0, col-1, len(b)-1)
                    rc = clamp(0, row-1, len(b[0])-1)
                    print("out of range (%d,%d), clamping to (%d,%d)" % (col-1, row-1, cc, rc))
                    


def get_char_for(wid):
    global lastchar
    global known_symbols
    global selected_char
    
    curr = lastchar
    lastchar = chr(ord(lastchar)+1)
    known_symbols.update({curr:wid})

    
    return curr 

def calc_affinity(l):
    d = Counter(l)
    so = sorted(d.items(), key=lambda x: x[1])
    if so:
        target_symbol = ((so[len(so)-1]))[0]
    
        #print(mydict.keys()[mydict.values().index(16)] # Prints george
        for k,v in known_symbols.items():
            if k == target_symbol:
                return v;
    return None
    
def window_char_up(startchar):
    for row in range(0,len(buffer[0])):
        bs=0
        hits=[]
        for col in range(0,len(buffer)):
            if(buffer[col][row] == startchar):
                #print("%c at (%d,%d)\n" % (startchar,row,col))
                
                for j in reversed(range(0,row)):
                    if buffer[col][j] == '0':
                        continue;
                    if buffer[col][j] != startchar:
                        hits.append(buffer[col][j])
                        break
                bs=1
                
        if hits:
            print("got hit" , hits)
            return hits
        else:
            print("no hits")
        if bs:
            break;

def window_char_down(startchar):
    for row in reversed(range(0,len(buffer[0]))):
        bs=0
        hits=[]
        for col in range(0,len(buffer)):
            if(buffer[col][row] == startchar):
                #print("%c at (%d,%d)\n" % (startchar,row,col))
                
                for j in range(row, len(buffer[0])):
                    if buffer[col][j] == '0':
                        continue;
                    if buffer[col][j] != startchar:
                        hits.append(buffer[col][j])
                        break
                bs=1
                
        if hits:
            print(hits)
            return hits
        else:
            print("no hits")
        if bs:
            break;

    
def print_buff(buff):
    sbuff = ""
    for row in range(0,len(buff[0])):
        for col in range(0,len(buff)):
        #thefile.write("%c" % buff[col][row])
            sbuff += str(buff[col][row])
        sbuff += "\n"
    
    print(sbuff)

if len(sys.argv) == 1:
    exit;

def transposed(lists):
   if not lists: return []
   return list(map(lambda *row: list(row), *lists))


xcmd = ["xprop", "-root"]
xprop_output = subprocess.check_output(xcmd).decode("utf-8")

desktop_geo = get_desktop_info(xprop_output)
stack = get_client_stack(xprop_output)

infos = []

for i in stack:
    winfo = get_window_info(i)
    if(winfo["title"]=="xfce4-panel"):
        continue
    
    infos.append(winfo)

#infos = infos[::-1]

for i in infos:
    i['char'] = get_char_for(i["wid"])
    w = int(i['wid'], 16);
    
    if w == get_active_window():
        i['is_selected'] = 1
        selected_char = i['char']
    else:
        i['is_selected'] = 0

#print(infos)
#print(desktop_geo)

buffer = create_test_buffer()
populate_buffer(buffer, infos)

if sys.argv[1]=="up":
    target_window_id = calc_affinity(window_char_up(selected_char))
elif sys.argv[1]=="down":
    target_window_id = calc_affinity(window_char_down(selected_char))
elif sys.argv[1]=="left":
    buffer = transposed(buffer)
    target_window_id = calc_affinity(window_char_up(selected_char))
    if not target_window_id:
        target_window_id = calc_affinity(window_char_down(selected_char))
elif sys.argv[1]=="right":
    buffer = transposed(buffer)
    target_window_id = calc_affinity(window_char_down(selected_char))
    if not target_window_id :
        target_window_id = calc_affinity(window_char_up(selected_char))
        
elif sys.argv[1]=="show":
    print_buff(buffer)
    exit(0)
else:
    print("unknown argument")
    exit(1)

def move_window(a, x, y):
    cmd = ["xdotool", "windowmove", a["wid"], str(x), str(y)]
    decoded = subprocess.check_output(cmd).decode("utf-8")


def resize_window(a, x, y):
    cmd = ["xdotool", "windowsize", a["wid"], str(x), str(y) ]
    print(cmd)
    decoded = subprocess.check_output(cmd).decode("utf-8")
    
    
def swap_windows(a,b):
    move_window(a, b["absoluteupperleftx"], b["absoluteupperlefty"])
    move_window(b, a["absoluteupperleftx"], a["absoluteupperlefty"])
    resize_window(a, b["width"], b["height"])
    resize_window(b, a["width"], a["height"])
    
if target_window_id:
    cmd = ["wmctrl", "-i", "-a", target_window_id]
    decoded = subprocess.check_output(cmd).decode("utf-8")
    print(decoded)

    for i in infos:
        if i['wid'] == target_window_id:
            break ;

    w = i["width"]
    h = i["height"]
    
    cmd = ["xdotool", "mousemove", "--window", str(target_window_id), str(w/2), str(h/2)]
    decoded = subprocess.check_output(cmd).decode("utf-8")
    print(decoded)

    if len(sys.argv) > 2:
        if sys.argv[2] == "swap":
            o = known_symbols[selected_char]
            n = target_window_id

            for i in infos:
                w = int(i['wid'], 16)
                if(w == int(o,16)):
                    target_info = i
                if(w == int(n,16)):
                    selected_info = i


            swap_windows(target_info, selected_info)
            print(o,n)
