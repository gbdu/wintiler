#!/usr/bin/python3
#
# Requires: xprop, xdotool, xwininfo, wmctrl
#
#       xprop: window stack order and desktop geometry
#       xdotool: identify selected window and move mouse
#       xwininfo: window geometry information
#       wmctrl: change focus


# READ layouts.conf
# Implement the rules

import sys
import os
import subprocess
import re
import configparser

from collections import Counter
import operator

# Config section:

scale = 16 # you can change this for a different "resolution"
lastchar='A' # You can use something like awesome font icons here (as
             # unicode chars that the term understands) end of config
             # section

# Globbals:
selected_char = ""
desktop_geo = None
known_symbols = {}
config_p = None
desktop_names_in_use = []
current_desktop_in_use = None
stack = None
infos = []

def get_active_window():
    cmd = ["xdotool", "getactivewindow"]

    decoded = subprocess.check_output(cmd).decode("utf-8")
    return int(decoded)

def parse_winfo(linfo):
    dinfo = {}
    print(linfo)
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
            
def get_desktops(xprop_output):

    x = xprop_output.find("_NET_DESKTOP_NAMES(UTF8_STRING)")
    if x != -1 :
        xo = xprop_output[x:]
        xx = xo.find("\n")
        if xx != -1:
            ds = xprop_output[x+33:x+xx]
            dnames = []
            for i in ds.split(","):
                dnames.append(i.replace("\"","")[1:])
            return dnames
            
def get_current_desktop(xprop_output,desktops):       
    x = xprop_output.find("_NET_CURRENT_DESKTOP(CARDINAL)")
    if x != -1 :
        xo = xprop_output[x:]
        xx = xo.find("\n")
        if xx != -1:
            ds = xprop_output[x+33:x+xx]
            curr_c = int(ds)
            return desktops[curr_c]
        else:
            return -1;
            
def get_window_info(win):
    cmd = ["xwininfo", "-id", "%s" % win]

    minfo = {}

    decoded = subprocess.check_output(cmd).decode("utf-8")

    winfo_as_list = decoded.split('\n')
    return parse_winfo(winfo_as_list)

def get_wm_class(win):
    cmd = ["xprop", "-id", "%s" % win["wid"]]
    decoded = subprocess.check_output(cmd).decode("utf-8")

    w = decoded.find("WM_CLASS(STRING)")
    wn = decoded[w+18:].split("\n")[0]
    wn = wn.split(",")[0]
    wn = wn.replace("\"","")
    wn = wn.replace(" ","")
    

    print("FFFFFF" , wn)
    return wn

def create_test_buffer(d=None):
    '''create diagramatic presentation of desktop of current desktop''' 
    global desktop_geo

    
    if not d:
        d = desktop_geo

    global scale
    global w
    global h
    #scale = 1
    w = int(d[0]/scale)
    h = int(d[1]/scale)

    print(w,h)
    print("-" * 60)
    print()

    buffer = [ [ '0' for x in range(h) ] for y in range(w)]
    return buffer

def clamp(minimum, x, maximum):
    return max(minimum, min(x, maximum))

def populate_buffer(b,winfos):
    # b is a list of columns (which are lists of chars)
    # scan each window
    print("loaded desktop geo and populated buffer", desktop_geo)
    for i in winfos:
        for col in range(int(i["absoluteupperleftx"]/scale),\
                         int(i["absoluteupperleftx"]/scale+i["width"]/scale)):
            for row in range(int(i["absoluteupperlefty"]/scale),\
                             int(i["absoluteupperlefty"]/scale+i["height"]/scale)):
                # print (col,row)
                try:
                    b[col-1][row-1] = i['char']
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
    else:
        return 
        #print(mydict.keys()[mydict.values().index(16)] # Prints george
    for k,v in known_symbols.items():
        if k == target_symbol:
            return v;
      
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
            print(hits)
            return hits
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

def transposed(lists):
   if not lists: return []
   return list(map(lambda *row: list(row), *lists))
def move_window(a, x, y):
    cmd = ["xdotool", "windowmove", a["wid"], str(x), str(y)]
    decoded = subprocess.check_output(cmd).decode("utf-8")

def resize_window(a, x, y):
    cmd = ["xdotool", "windowsize", a["wid"], str(x), str(y) ]
    print(cmd)
    decoded = subprocess.check_output(cmd).decode("utf-8")

def move_window_s(a, place):
    """Move window into semantic place (topleft, topright, bottomleft, bottomright, center)"""
    global desktop_geo
    paddingx = 5
    paddingy = 30

    if place == "center":
        cmd = ["xdotool", "windowmove", a["wid"], str(paddingx*5), str(paddingy)]
        decoded = subprocess.check_output(cmd).decode("utf-8")

        cmd = ["xdotool", "windowsize", a["wid"], str(desktop_geo[0]-paddingx*10), str(desktop_geo[1]-paddingy*1.5)]
        decoded = subprocess.check_output(cmd).decode("utf-8")     
        
    if place == "left":
        cmd = ["xdotool", "windowmove", a["wid"], str(paddingx), str(paddingy)]
        decoded = subprocess.check_output(cmd).decode("utf-8")

        cmd = ["xdotool", "windowsize", a["wid"], str(desktop_geo[0]/2-paddingx), str(desktop_geo[1]-paddingy)]
        decoded = subprocess.check_output(cmd).decode("utf-8")     

    if place == "right":
        cmd = ["xdotool", "windowmove", a["wid"], str(desktop_geo[0]/2-paddingx), str(paddingy)]
        decoded = subprocess.check_output(cmd).decode("utf-8")

        cmd = ["xdotool", "windowsize", a["wid"], str(desktop_geo[0]/2-paddingx), str(desktop_geo[1]-paddingy)]
        decoded = subprocess.check_output(cmd).decode("utf-8")     

        pass
    if place == "bottom":
        pass
    if place == "top":
        pass
    if place == "topleft":

        cmd = ["xdotool", "windowmove", a["wid"], str(paddingx), str(paddingy)]
        decoded = subprocess.check_output(cmd).decode("utf-8")

        cmd = ["xdotool", "windowsize", a["wid"], str(desktop_geo[0]/2-paddingx*5), str(desktop_geo[1]/2-paddingy*1.5)]
        decoded = subprocess.check_output(cmd).decode("utf-8")     

    if place == "topright":
        pass
    if place == "bottomright":
        pass
    if place == "bottomleft":

        cmd = ["xdotool", "windowmove", a["wid"], str(paddingx), str(desktop_geo[1]/2)]
        decoded = subprocess.check_output(cmd).decode("utf-8")

        cmd = ["xdotool", "windowsize", a["wid"], str(desktop_geo[0]/2-paddingx*5), str(desktop_geo[1]/2)]
        decoded = subprocess.check_output(cmd).decode("utf-8")     
    
def xprop_populate():
    global w
    global desktop_geo
    global desktop_names_in_use
    global current_desktop_in_use
    global stack
    global infos
    
    xcmd = ["xprop", "-root"]
    xprop_output = subprocess.check_output(xcmd).decode("utf-8")
    desktop_geo = get_desktop_info(xprop_output)
    stack = get_client_stack(xprop_output)
    


    desktop_names_in_use = get_desktops(xprop_output)
    current_desktop_in_use = get_current_desktop(xprop_output,desktop_names_in_use)
    print(current_desktop_in_use)
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

    return infos

def set_transparency(w,val):
    # cmd = ["transset-df -p --inc 0.2", "windowmove", a["wid"], str(paddingx), str(paddingy)]
    # decoded = subprocess.check_output(cmd).decode("utf-8")

    pass
def read_conf(filename):
 """
 Keyword Arguments:
 filename -- filepath to the layouts.conf file
 synopsis: read the layouts.conf
 """
     
def swap_windows(a,b):
    move_window(a, b["absoluteupperleftx"], b["absoluteupperlefty"])
    move_window(b, a["absoluteupperleftx"], a["absoluteupperlefty"])
    resize_window(a, b["width"], b["height"])
    resize_window(b, a["width"], a["height"])
def print_help():
    print("unknown arguments, use: wintile.py tile1)");
    
def read_config():
    global config_p
    
    config_p = configparser.ConfigParser()
    config_p.read("/home/garg/wintilepy/layouts.conf")
    # TODO get rid of "garg" and replace with user name
    print("read sections")
    print(config_p.sections())
    
def retile():   
    '''retile entire desktop based on layouts.conf'''
    global config_p
    global current_desktop_in_use
    global stack
    global infos
    
    if not stack:
        print("Error in stack");
        return -1;
    if not config_p:
        print("error in reading config")
        return -2;
    if not current_desktop_in_use:
        print("error in reading current desktop in use")
        return -3;     
    if current_desktop_in_use == -1:
        print("warning: unknown current desktop cardinal (error reading xprop output)")
        return -4;
    
    # First, see if the current desktop is mentioned in layouts.conf:   
    for i in config_p.sections():
        if i == current_desktop_in_use:
            # ok, good, implement the layout
            # 1.) go through the stack of current windows
            # 2.) if in layout, implement, if not, set transparency and keep going
            for c,value in enumerate(infos):
                desired_pos = None
                wmname = get_wm_class(value)
                if wmname in config_p[current_desktop_in_use]:
                    # implement it 
                    desired_pos = config_p[current_desktop_in_use].get(wmname)
                if not desired_pos :
                    # TODO minimize or shade ? transparency? 
                    continue;
                else:
                    #print("moving", value, "to ", desired_pos);

                    if value["is_selected"]:
                        in_stacked_layer_selected = True
                    move_window_s(value, desired_pos);            
               # else: print("no", value["title"])
    
if __name__ ==  "__main__":
    if len(sys.argv) == 1:
        print("not enough arguments\n")
        print_help()
        exit;

    read_config()
    infos = xprop_populate()
    buffer = create_test_buffer()
    populate_buffer(buffer, infos)

    if sys.argv[1]=="sort1":
        target_window_id = calc_affinity(window_char_up(selected_char))
        retile();
    elif sys.argv[1]=="tile1":
        target_window_id = calc_affinity(window_char_down(selected_char))
    elif sys.argv[1]=="show":
        print_buff(buffer)
        exit(0)
    else:
        print_help()
    exit(1)


# if target_window_id:
#     cmd = ["wmctrl", "-i", "-a", target_window_id]
#     decoded = subprocess.check_output(cmd).decode("utf-8")
#     print(decoded)

#     for i in infos:
#         if i['wid'] == target_window_id:
#             break ;

#     w = i["width"]
#     h = i["height"]
    
#     cmd = ["xdotool", "mousemove", "--window", str(target_window_id), str(w/2), str(h/2)]
#     decoded = subprocess.check_output(cmd).decode("utf-8")
#     print(decoded)

#     if len(sys.argv) > 2:
#         if sys.argv[2] == "swap":
#             o = known_symbols[selected_char]
#             n = target_window_id

#             for i in infos:
#                 w = int(i['wid'], 16)
#                 if(w == int(o,16)):
#                     target_info = i
#                 if(w == int(n,16)):
#                     selected_info = i


#             swap_windows(target_info, selected_info)
#             print(o,n)
