#!/bin/zsh
../tools/usbliter8ctl boot ./Ramdisk/iBSS.raw;
sleep 3;

idevicerestore -s "http://127.0.0.1:1337" -e -y CFW;