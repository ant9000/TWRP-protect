#!/usr/bin/env python3

import os, sys, shutil, subprocess, re
import urllib.request
import xml.etree.ElementTree as ET

# Determine current platform
plat = sys.platform

# Change current working dir to where the script is located
os.chdir(os.path.realpath(os.path.dirname(sys.argv[0])))

if not os.path.isdir('downloads'):
    os.mkdir('downloads')

# Download Android Image Kitchen for the current platform
AIK = {
    'win32': {
        'file':   'Android.Image.Kitchen.v3.2-Win32.zip',
        'url':    'https://forum.xda-developers.com/attachment.php?attachmentid=4452163&d=1521512064',
        'dir':    'Android Image Kitchen',
        'unpack': 'Android Image Kitchen/unpackimg.bat',
        'repack': 'Android Image Kitchen/repackimg.bat',
        'clean':  'Android Image Kitchen/cleanup.bat',
    },
    'linux': {
        'file':   'AIK-Linux-v3.2-ALL.tar.gz',
        'url':    'https://forum.xda-developers.com/attachment.php?attachmentid=4452164&d=1521512064',
        'dir':    'AIK-Linux',
        'unpack': 'AIK-Linux/unpackimg.sh',
        'repack': 'AIK-Linux/repackimg.sh',
        'clean':  'AIK-Linux/cleanup.sh',
    },
}

aik = AIK.get(plat, None)
if not aik:
    print("No AIK available for '%s', sorry." % plat)
    sys.exit(1)

aik_path = 'downloads/%s' % aik['file']
if not os.path.isfile(aik_path):
    print('No AIK found, downloading it.')
    with open(aik_path,'wb') as f:
        with urllib.request.urlopen(aik['url']) as r:
            f.write(r.read())
    shutil.unpack_archive(aik_path)

# Download TWRP portrait.xml, landscape.xml
for theme in ['portrait.xml', 'landscape.xml']:
    theme_url  = 'https://raw.githubusercontent.com/ant9000/android_bootable_recovery/android-8.1/gui/theme/common/%s' % theme
    theme_path = 'downloads/%s' % theme
    if not os.path.isfile(theme_path):
        print('Downloading {0} with password support.'.format(theme))
        with open(theme_path,'wb') as f:
            with urllib.request.urlopen(theme_url) as r:
                f.write(r.read())

# Choose the TWRP image to password protect
image_path = ''
if len(sys.argv) > 1:
    image_path = sys.argv[1]
while not os.path.isfile(image_path):
    image_path = input('Enter the TWRP recovery image that you want to protect: ')

# Enter the desired password
password = ''
while password == '':
    password = input('Password to be used in TWRP recovery: ')

# Unpack image
try:
    print('Unpacking image {0}.'.format(image_path))
    ret = subprocess.run([aik['unpack'],image_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ret.returncode < 0:
        print('Unpack image killed with signal {0}'.format(-ret.returncode))
        sys.exit(1)
except Exception as e:
    print("Error: {0}".format(e))
    sys.exit(1)

theme_path = ''
for theme in ['portrait.xml', 'landscape.xml']:
    theme_path = os.path.join(aik['dir'],'ramdisk','twres',theme)
    if os.path.isfile(theme_path):
        break
if not os.path.isfile(theme_path):
    print("The image '{0}' does not look like a TWRP image.".format(image_path))
    sys.exit(1)
    
# Overwrite portrait.xml or landscape.xml
tree = ET.parse('downloads/{0}'.format(os.path.basename(theme_path)))
root = tree.getroot()
for action in root.find("*/page[@name='clear_vars']/action").iter('action'):
    if action.text == 'tw_unlock_pass=0':
        action.text = 'tw_unlock_pass=' + password
### requires root ON Linux
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','a+w',theme_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
tree.write(theme_path)
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','go-w',theme_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Activate secure adb
default_prop_path = os.path.join(aik['dir'],'ramdisk','default.prop')
prop = re.sub('^ro.adb.secure=0$', 'ro.adb.secure=1', open(default_prop_path).read(), flags=re.MULTILINE)
### requires root ON Linux
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','a+w',default_prop_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
open(default_prop_path,'w').write(prop)
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','go-w',default_prop_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

# Repack image
try:
    print('Repacking image {0}.'.format(image_path))
    ret = subprocess.run([aik['repack']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ret.returncode < 0:
        print('Repack image killed with signal {0}'.format(-ret.returncode))
        sys.exit(1)
except Exception as e:
    print("Error: {0}".format(e))
    sys.exit(1)

# Move protected image
protected_path = image_path+'.protected'
shutil.copy(os.path.join(aik['dir'],'image-new.img'),protected_path)
print("Protected image available as '{0}'.".format(protected_path))

# Cleanup
try:
    ret = subprocess.run([aik['clean']], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if ret.returncode < 0:
        print('Clean killed with signal {0}'.format(-ret.returncode))
        sys.exit(1)
except Exception as e:
    print("Error: {0}".format(e))
    sys.exit(1)
