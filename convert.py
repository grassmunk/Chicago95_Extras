#!/usr/bin/env python3

# Quick and dirty copy from pluslib to make SVG files from ico/png files
# GPL3
# Grassmunk

import io
import os
import sys
import json
import struct
import shutil
import logging
import svgwrite
import PIL.Image
import subprocess
import configparser
import logging.handlers
import xml.etree.ElementTree as ET

from pathlib import Path
from pprint import pprint
from configparser import ConfigParser
from PIL import BmpImagePlugin, PngImagePlugin, Image

max_colors=32
overlap=1
squaresize=20

def convert_icon(icon_file_path, target_folder='./', tmp_file="./chicago95_tmp_file.svg"):
    ## Converts Icons to PNG
    # Input:
    #  folder: svg file destination folder
    #  icon_file_path: theme icon file to be processed
    #  tmp_file: tmp working file for inkscape

    # Lots of code lifted from pixel2svg

    path_to_icon, icon_file_name = os.path.split(icon_file_path)
    icon_name, icon_ext = os.path.splitext(icon_file_name)
    svg_name = icon_name+".svg"

    print("{:<21} | Converting {} to {} using pixel2svg".format("", icon_file_path, svg_name))
    # Open the icon file
    try:
        image = Image.open(icon_file_path)
    except IOError:
        print("{:<21} | Image BMP compression not support, converting".format(""))


    image = image.convert("RGBA")
    (width, height) = image.size
    rgb_values = list(image.getdata())
    rgb_values = list(image.getdata())
    svgdoc = svgwrite.Drawing(filename = target_folder + svg_name,
                            size = ("{0}px".format(width * squaresize),
                            "{0}px".format(height * squaresize)))

    rectangle_size = ("{0}px".format(squaresize + overlap),
                    "{0}px".format(squaresize + overlap))
    rowcount = 0
    while rowcount < height:
        colcount = 0
        while colcount < width:
            rgb_tuple = rgb_values.pop(0)
            # Omit transparent pixels
            if rgb_tuple[3] > 0:
                rectangle_posn = ("{0}px".format(colcount * squaresize),
                        "{0}px".format(rowcount * squaresize))
                rectangle_fill = svgwrite.rgb(rgb_tuple[0], rgb_tuple[1], rgb_tuple[2])
                alpha = rgb_tuple[3];
                if alpha == 255:
                    svgdoc.add(svgdoc.rect(insert = rectangle_posn,
                                size = rectangle_size,
                                fill = rectangle_fill))
                else:
                    svgdoc.add(svgdoc.rect(insert = rectangle_posn,
                                size = rectangle_size,
                                fill = rectangle_fill,
                                opacity = alpha/float(255)))
            colcount = colcount + 1
        rowcount = rowcount + 1
    svgdoc.save()
    print("{:<21} | Prelim SVG created: {}".format("", target_folder + svg_name))

    convert_to_proper_svg_with_inkscape(tmp_file, svgdoc.filename)
    SVG_NS = "http://www.w3.org/2000/svg"
    svg = ET.parse(tmp_file)
    rects = svg.findall('.//{%s}rect' % SVG_NS)
    rgbs = {}
    for rect in rects:
        rect_id = rect.attrib['id']
        rgb = rect.attrib['fill']
        if rgb not in rgbs:
            rgbs[rgb] = rect_id


    print("{:<21} | Inkscape will open {} times to process {}".format("", min(len(rgbs), max_colors), target_folder + svg_name))

    count = 0
    for rgb in rgbs:
        count = count + 1
        if len(rgbs) >= max_colors:
            print("{:<21} | Max colors ({}) hit exiting conversion".format("", max_colors))
            break
        print("{:<21} | [{:<3} / {:<3} {:<5}] Converting {}".format("", count, len(rgbs),str(round((float(count)/float(len(rgbs))*100),0)), rgb ))
        fix_with_inkscape( rgbs[rgb] , tmp_file )

    shutil.move(tmp_file, svgdoc.filename)
    return(svgdoc.filename)


def convert_to_proper_svg_with_inkscape(svg_out, svg_in):
    print("{:<21} | Converting {} to {} with Inkscape".format("",svg_out, svg_in))
    # this is a bit of a hack to support both version of inkscape
    inkscape_path = subprocess.check_output(["which", "inkscape"]).strip().decode('ascii')
    inkscape_version_cmd = subprocess.check_output([inkscape_path, "--version"])
    inkscape_version = inkscape_version_cmd.splitlines()[0].split()[1].decode().split(".")[0]
    print(inkscape_path)
    if int(inkscape_version) < 1:
        print("{:<21} | Using Inkscape v0.9x command".format(''))
        # Works with version 0.9x
        args = [
        inkscape_path,
        "-l", svg_out, svg_in
        ]
    else:
        print("{:<21} | Using Inkscape v1.0 command".format(''))
        #works with version 1.0
        args = [
        inkscape_path,
        "-l", "-o", svg_out, svg_in
        ]

    subprocess.check_call(args, stderr=subprocess.DEVNULL ,stdout=subprocess.DEVNULL)

def fix_with_inkscape(color, tmpfile):
    print("{:<21} | Combining {} in {}".format("",color, tmpfile))
    inkscape_path = subprocess.check_output(["which", "inkscape"]).strip()

    inkscape_version_cmd = subprocess.check_output([inkscape_path, "--version"])
    inkscape_version = inkscape_version_cmd.splitlines()[0].split()[1].decode().split(".")[0]

    if int(inkscape_version) < 1:
        args = [
        inkscape_path,
        "--select="+color,
        "--verb", "EditSelectSameFillColor",
        "--verb", "SelectionCombine",
        "--verb", "SelectionUnion",
        "--verb", "FileSave",
        "--verb", "FileQuit",
        tmpfile
        ]
    else:
        args = [
        inkscape_path,
        "-g",
        "--select="+color,
        "--verb", "EditSelectSameFillColor;SelectionCombine;SelectionUnion;FileSave;FileQuit",
        tmpfile
        ]

    subprocess.check_call(args, stderr=subprocess.DEVNULL ,stdout=subprocess.DEVNULL)


def convert_to_png_with_inkscape(svg_in, size, png_out):
    print("{:<21} | Converting {} to {} of size {}".format("", svg_in, png_out, size))
    inkscape_path = subprocess.check_output(["which", "inkscape"]).strip()

    inkscape_version_cmd = subprocess.check_output([inkscape_path, "--version"])
    inkscape_version = inkscape_version_cmd.splitlines()[0].split()[1].decode().split(".")[0]

    size = str(size)

    if int(inkscape_version) < 1:
        args = [
        inkscape_path,
        "--without-gui",
        "-f", svg_in,
        "--export-area-page",
        "-w", size,
        "-h", size,
        "--export-png=" + png_out
        ]
    else:
        args = [
        inkscape_path,
        "--export-area-page",
        "--export-type=png",
        "-w", size,
        "-h", size,
        "-o", png_out,
        svg_in
        ]

fname = convert_icon(icon_file_path=sys.argv[1])

# convert_to_png_with_inkscape(fname, 32, "./32.png")