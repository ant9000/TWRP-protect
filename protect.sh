#!/bin/bash

#change working dir to where the script is located
me=$0
while [ -L "$me" ]; do me=$(file -- "$me"|cut -f2 -d\`|cut -f1 -d\'); done
BASE="`cd -P -- "$(dirname -- "$me")" && pwd -P`"
cd $BASE

if [ ! -d downloads ]; then
  mkdir downloads
fi

if [ ! -f downloads/AIK-Linux-v3.2-ALL.tar.gz ]; then
  wget -O downloads/AIK-Linux-v3.2-ALL.tar.gz \
    "https://forum.xda-developers.com/attachment.php?attachmentid=4452164&d=1521512064"
fi

if [ ! -d AIK-Linux ]; then
  tar xvf downloads/AIK-Linux-v3.2-ALL.tar.gz
fi

if [ ! -f downloads/portrait.xml ]; then
  wget -O downloads/portrait.xml \
    https://raw.githubusercontent.com/ant9000/android_bootable_recovery/android-8.1/gui/theme/common/portrait.xml
fi

if [ ! -f downloads/landscape.xml ]; then
  wget -O downloads/landscape.xml \
    https://raw.githubusercontent.com/ant9000/android_bootable_recovery/android-8.1/gui/theme/common/landscape.xml
fi

twrp_image="$1"
if [ -z $twrp_image ]; then
  read -p "Enter the TWRP recovery image that you want to protect: " twrp_image
fi

if [ ! -f $twrp_image ]; then
  echo "No such file '$twrp_image'"
  exit 1
fi

read -p "Password to be used in TWRP recovery (if you need a \\, type it twice): " -s password
echo
if [ -z $password ]; then
  echo "No password given, quitting."
  exit 2
fi

# Protect special characters:
#  $ -> \$
#  ! -> \!
#  & -> &amp;
#  < -> &lt;
#  > -> &gt;
password=`echo "$password" | sed 's/\\\\/\\\\\\\/g; s/\\$/\\\\$/g; s/\!/\\!/g; s/&/\&amp;/g; s/>/\&gt;/g; s/</\&lt;/g;'`

echo "For unpacking/repacking the image, root rights are needed."
sudo -v 
AIK-Linux/unpackimg.sh "$twrp_image"
status=$?
if [ $status -ne 0 ]; then
  echo "Unpack image failed (exit code $status)."
  echo "Releasing root rights."
  sudo -k
  exit $status
fi

if [ -f AIK-Linux/ramdisk/twres/portrait.xml ]; then
  perl -pe "s{<action function=\"set\">tw_unlock_pass=.+</action>}{<action function=\"set\">tw_unlock_pass=$password</action>}" \
    downloads/portrait.xml | sudo tee AIK-Linux/ramdisk/twres/portrait.xml >/dev/null
elif [ -f AIK-Linux/ramdisk/twres/landscape.xml ]; then
  perl -pe "s{<action function=\"set\">tw_unlock_pass=.+</action>}{<action function=\"set\">tw_unlock_pass=$password</action>}" \
    downloads/landscape.xml | sudo tee AIK-Linux/ramdisk/twres/landscape.xml >/dev/null
else
  echo "The image '$twrp_image' does not look like a TWRP image."
  echo "Releasing root rights."
  sudo -k 
fi

sudo sed -i 's/ro.adb.secure=0/ro.adb.secure=1/' AIK-Linux/ramdisk/default.prop

out_image=`basename "$twrp_image"`.protected
AIK-Linux/repackimg.sh
mv AIK-Linux/image-new.img "$out_image"
AIK-Linux/cleanup.sh

echo "Releasing root rights."
sudo -k 

echo "Your protected image is '$out_image'."
echo
