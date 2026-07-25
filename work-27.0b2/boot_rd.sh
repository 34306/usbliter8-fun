#!/bin/zsh
../tools/usbliter8ctl boot ./Ramdisk/iBSS.raw;
sleep 3;
irecovery -f Ramdisk/iBEC.img4;
irecovery -c go;

sleep 2;
irecovery -f Ramdisk/RestoreLogo.img4;
irecovery -c "setpicture 0x1"
irecovery -c "bgcolor 0 191 255"    # sky background color

irecovery -f Ramdisk/ANE.img4;
irecovery -c firmware;

irecovery -f Ramdisk/AOP.img4;
irecovery -c firmware;

irecovery -f Ramdisk/AVE.img4;
irecovery -c firmware;

sleep 1;
irecovery -f Ramdisk/SPTM.img4;
irecovery -c firmware;

sleep 3;
irecovery -f Ramdisk/TXM.img4;
irecovery -c firmware;

irecovery -f Ramdisk/GFX.img4;
irecovery -c firmware;

irecovery -f Ramdisk/ISP.img4;
irecovery -c firmware;

sleep 1;
irecovery -f Ramdisk/PMP.img4;
irecovery -c firmware;

irecovery -f Ramdisk/RestoreTrustCache.img4;
irecovery -c firmware;

irecovery -f Ramdisk/SIO.img4;
irecovery -c firmware;

irecovery -f Ramdisk/WCH.img4;
irecovery -c firmware;

irecovery -f Ramdisk/RestoreRamdisk.img4;
irecovery -c "getenv ramdisk-delay"
irecovery -c ramdisk;

sleep 2;
irecovery -f Ramdisk/DeviceTree.img4;
irecovery -c devicetree;

irecovery -f Ramdisk/SEP.img4;
irecovery -c rsepfirmware;

irecovery -f Ramdisk/Kernelcache.img4;
irecovery -c bootx;
sleep 1;