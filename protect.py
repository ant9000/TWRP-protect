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

def fetch(url):
    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'Wget/1.18 (linux-gnu)')
    return urllib.request.urlopen(req)

# Download Android Image Kitchen for the current platform
AIK = {
    'URL':   'https://forum.xda-developers.com/showthread.php?t=2073775',
    'win32': {
        'regex':  'Android\.Image\.Kitchen',
        'dir':    'Android Image Kitchen',
        'unpack': 'Android Image Kitchen/unpackimg.bat',
        'repack': 'Android Image Kitchen/repackimg.bat',
        'clean':  'Android Image Kitchen/cleanup.bat',
    },
    'linux': {
        'regex':  'AIK-Linux',
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

try:
    if not os.path.isdir(aik['dir']):
        print('Finding AIK download url... ', end='', flush=True)
        response = fetch(AIK['URL'])
        html = str(response.read())
        regex = '<a href="(http[^"]+)"[^>]*>({}[^<]+)<'.format(AIK[sys.platform]['regex'])
        print('done.')
        download = re.findall(regex, html)[0]
        aik_url, aik_name = download

        aik_path = 'downloads/%s' % aik_name
        if not os.path.isfile(aik_path):
            print('Downloading {}: '.format(aik_name), end='', flush=True)
            with fetch(aik_url) as response:
                with open(aik_path,'wb') as f:
                    chunk = response.read(10240)
                    while chunk:
                        print('.', end='', flush=True)
                        f.write(chunk)
                        chunk = response.read(10240)
                print('done')

            print('Extracting archive... ', end='', flush=True)
            shutil.unpack_archive(aik_path)
            print('done.')

    # Download TWRP portrait.xml, landscape.xml
    for theme in ['portrait.xml', 'landscape.xml']:
        theme_url  = 'https://raw.githubusercontent.com/ant9000/android_bootable_recovery/android-8.1/gui/theme/common/%s' % theme
        theme_path = 'downloads/%s' % theme
        if not os.path.isfile(theme_path):
            print('Downloading {0} with password support.'.format(theme))
            with open(theme_path,'wb') as f:
                with fetch(theme_url) as r:
                    f.write(r.read())

except Exception as e:
    print("Error: {0}".format(e))
    sys.exit(1)

# Choose the TWRP image to password protect
image_path = ''
if len(sys.argv) > 1:
    image_path = os.path.join('.', sys.argv[1])
while not os.path.isfile(image_path):
    image_path = input('Enter the TWRP recovery image that you want to protect: ')

# Enter the desired password
password = ''
while password == '':
    password = input('Password to be used in TWRP recovery: ')

# Obtain sudo access, needed by AIK on Linux
if plat == 'linux':
    print("For unpacking/repacking the image, root rights are needed.")
    try:
        ret = subprocess.run(['sudo','-v'])
    except Exception as e:
        print("Error: {0}".format(e))
        sys.exit(1)

# Unpack image
try:
    print('Unpacking image {0}.'.format(image_path))
    ret = subprocess.run([aik['unpack'],image_path])
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
    ret = subprocess.run(['sudo','chmod','a+w',theme_path])
tree.write(theme_path)
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','go-w',theme_path])

# Activate secure adb
default_prop_path = os.path.join(aik['dir'],'ramdisk','default.prop')
prop = re.sub('^ro.adb.secure=0$', 'ro.adb.secure=1', open(default_prop_path).read(), flags=re.MULTILINE)
### requires root ON Linux
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','a+w',default_prop_path])
open(default_prop_path,'w').write(prop)
if plat == 'linux':
    ret = subprocess.run(['sudo','chmod','go-w',default_prop_path])

# Repack image
try:
    print('Repacking image {0}.'.format(image_path))
    ret = subprocess.run([aik['repack']])
    if ret.returncode < 0:
        print('Repack image killed with signal {0}'.format(-ret.returncode))
        sys.exit(1)
except Exception as e:
    print("Error: {0}".format(e))
    sys.exit(1)

# Move protected image
protected_path = image_path+'.protected'
shutil.copy(os.path.join(aik['dir'],'image-new.img'),protected_path)

# Cleanup
try:
    ret = subprocess.run([aik['clean']])
    if ret.returncode < 0:
        print('Clean killed with signal {0}'.format(-ret.returncode))
        sys.exit(1)
except Exception as e:
    print("Error: {0}".format(e))

if plat == 'linux':
    print("Releasing root rights.")
    try:
        ret = subprocess.run(['sudo','-k'])
    except Exception as e:
        print("Error: {0}".format(e))

print("Your protected image is '{0}'.".format(protected_path))
