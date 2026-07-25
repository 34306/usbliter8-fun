#!/usr/bin/env python3.14
import struct
import os
import sys
import glob
import subprocess
from pathlib import Path

fp = None

def patch(offset, data):
    file_offset = offset
    
    if isinstance(data, int):
        data = struct.pack('<I', data)
    if isinstance(data, str):
        data = data.encode()

    fp.seek(file_offset)
    fp.write(data)
    fp.flush()

os.system("rm -rf Ramdisk")
os.system("mkdir Ramdisk")

# 1. Grab & Patch iBSS 
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p -o Ramdisk/iBSS.raw")
fp = open("Ramdisk/iBSS.raw", "r+b")
# Keep nonce
# NONC: 586df1f9fa995b4c056ecd88f2fd755c0c74e3712fe1dd5bcd0ca4991875f148
# SNON: 5f179f3695cb1ccf66f5376db3b7eef9e67f51e2
patch(0x36bd0, 0x1400000a)      # b #0x28
# Notice if loaded PATCHED iBSS (optional)
# patch(0x2C0, "PATCHED")
# patch(0x13CAD1, "PATCHED_1")
# patch image4_validate_property_callback
patch(0x23DB0, 0xd503201f)      # nop
patch(0x23DB4, 0xd2800000)      # mov x0, #0
# patch boot-args with "rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2AFBC, 0xB0000542)      # adrp x2, #0xa9000
patch(0x2AFC0, 0x91214042)      # add x2, x2, #0x850
patch(0xD3850, "rd=md0 -v wdt=-1 debug=0x2014e\x00")  # for ramdisk boot
fp.close()

# 2. Grab & Patch iBEC
# FYI, iBEC load address = 0x19c050000
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBEC.d421.RELEASE.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBEC.d421.RELEASE.im4p -o iBEC.raw")
fp = open("iBEC.raw", "r+b")
# Notice if loaded PATCHED iBEC (optional)
# patch(0x2C0, "PATCHED")
# patch(0x13CAD1, "PATCHED_2")
# Keep nonce
patch(0x36bd0, 0x1400000a)      # b #0x28
# patch image4_validate_property_callback
patch(0x23DB0, 0xd503201f)      # nop
patch(0x23DB4, 0xd2800000)      # mov x0, #0
# PREVENT UNKNOWN PANIC
# patch(0x9706C, 0xd503201f)      # nop
# patch boot-args with "rd=md0 rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2AFBC, 0xB0000542)      # adrp x2, #0xa9000
patch(0x2AFC0, 0x91214042)      # add x2, x2, #0x850
patch(0xD3850, "rd=md0 -v wdt=-1 debug=0x2014e\x00")  # for ramdisk boot
fp.close()
os.system("../tools/img4tool -c iBEC.im4p -t ibec iBEC.raw")
os.system("../tools/img4 -i iBEC.im4p -o Ramdisk/iBEC.img4 -M t8030_apticket.der")

# 3. Grab AppleLogo
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/applelogo@3x~iphone.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/applelogo@3x~iphone.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/applelogo@3x~iphone.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/applelogo@3x~iphone.im4p.bak -o Ramdisk/RestoreLogo.img4 -M t8030_apticket.der -T rlgo")

# 4. Grab Other Components...
# ANE
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ane/h12_ane_fw_metis.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ane/h12_ane_fw_metis.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ane/h12_ane_fw_metis.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ane/h12_ane_fw_metis.im4p.bak -o Ramdisk/ANE.img4 -M t8030_apticket.der -T anef")

# AOP
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p.bak -o Ramdisk/AOP.img4 -M t8030_apticket.der -T aopf")

# AVE
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ave/AppleAVE2FW_H12.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ave/AppleAVE2FW_H12.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ave/AppleAVE2FW_H12.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/ave/AppleAVE2FW_H12.im4p.bak -o Ramdisk/AVE.img4 -M t8030_apticket.der -T avef")

# SPTM
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/sptm.t8030.release.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/sptm.t8030.release.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/sptm.t8030.release.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/sptm.t8030.release.im4p.bak -o Ramdisk/SPTM.img4 -M t8030_apticket.der -T sptm")

# TXM with patching
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/txm.iphoneos.release.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/txm.iphoneos.release.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/txm.iphoneos.release.im4p.bak")
os.system("pyimg4 im4p extract -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/txm.iphoneos.release.im4p.bak -o TXM.raw")
# patch 
fp = open("TXM.raw", "r+b")
# Patch TXM for make running binary which is not registered in trustcache
# TXM [Error]: CodeSignature: selector: 24 | 0xA8 | 0x30 | 1
patch(0x39fac, 0xd2800000)      # memcmp in _queryModule2
patch(0x39cb0, 0xd2800000)      # memcmp in _queryModule0
patch(0x39e18, 0xd2800000)      # memcmp in _queryModule1
# TXM [Error]: CodeSignature: selector: 24 | 0xA1 | 0x30 | 1
patch(0x3f564, 0xd503201f)          # instr in _validateConstraintsSignatureType
patch(0x3f56c, 0xd503201f)          # instr in _validateConstraintsSignatureType
fp.close()
#create im4p
os.system("pyimg4 im4p create -i TXM.raw -o TXM.im4p -d 1 -f trxm --lzfse")
# preserve payp structure
txm_im4p_data = Path('iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/txm.iphoneos.release.im4p.bak').read_bytes()
payp_offset = txm_im4p_data.rfind(b'PAYP')
if payp_offset == -1:
    print("Couldn't find payp structure !!!")
    sys.exit()

with open('TXM.im4p', 'ab') as f:
    f.write(txm_im4p_data[(payp_offset-10):])

payp_sz = len(txm_im4p_data[(payp_offset-10):])
print(f"payp sz: {payp_sz}")

txm_im4p_data = bytearray(open('TXM.im4p', 'rb').read())
txm_im4p_data[2:5] = (int.from_bytes(txm_im4p_data[2:5], 'big') + payp_sz).to_bytes(3, 'big')
open('TXM.im4p', 'wb').write(txm_im4p_data)

# sign
os.system("pyimg4 img4 create -p TXM.im4p -d 1 -o Ramdisk/TXM.img4 -m t8030_apticket.der")

# GFX
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/agx/armfw_g12p.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/agx/armfw_g12p.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/agx/armfw_g12p.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/agx/armfw_g12p.im4p.bak -o Ramdisk/GFX.img4 -M t8030_apticket.der -T gfxf")

# ISP
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/isp_bni/adc-zelus-d4x.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/isp_bni/adc-zelus-d4x.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/isp_bni/adc-zelus-d4x.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/isp_bni/adc-zelus-d4x.im4p.bak -o Ramdisk/ISP.img4 -M t8030_apticket.der -T ispf")

# PMP
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/pmp/t8030pmp.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/pmp/t8030pmp.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/pmp/t8030pmp.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/pmp/t8030pmp.im4p.bak -o Ramdisk/PMP.img4 -M t8030_apticket.der -T pmpf")

# RestoreTrustCache
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/094-13753-132.dmg.trustcache.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/094-13753-132.dmg.trustcache iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/094-13753-132.dmg.trustcache.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/094-13753-132.dmg.trustcache.bak -o Ramdisk/RestoreTrustCache.img4 -M t8030_apticket.der -T rtsc")

# SIO
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/SmartIOFirmware_ASCv2.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/SmartIOFirmware_ASCv2.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/SmartIOFirmware_ASCv2.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/SmartIOFirmware_ASCv2.im4p.bak -o Ramdisk/SIO.img4 -M t8030_apticket.der -T siof")

# WCH
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/WirelessPower/WirelessPower.iphone12.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/WirelessPower/WirelessPower.iphone12.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/WirelessPower/WirelessPower.iphone12.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/WirelessPower/WirelessPower.iphone12.im4p.bak -o Ramdisk/WCH.img4 -M t8030_apticket.der -T wchf")

# RestoreRamdisk
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/094-13753-132.dmg.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/094-13753-132.dmg iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/094-13753-132.dmg.bak")
# 8. Grab ramdisk & build custom ramdisk
os.system("pyimg4 im4p extract -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/094-13753-132.dmg.bak -o ramdisk.dmg")
# 
os.system("mkdir SSHRD")
os.system("sudo -A hdiutil attach -mountpoint SSHRD ramdisk.dmg -owners off")
os.system("sudo -A hdiutil create -size 254m -imagekey diskimage-class=CRawDiskImage -format UDZO -fs APFS -layout NONE -srcfolder SSHRD -copyuid root ramdisk1.dmg")
os.system("sudo -A hdiutil detach -force SSHRD")
os.system("sudo -A hdiutil attach -mountpoint SSHRD ramdisk1.dmg -owners off")
# sys.stdin.read(1)
#remove unneccessary files for expand space
os.system("sudo -A ../tools/gtar -x --no-overwrite-dir -f ssh.tar.gz -C SSHRD/")
os.system("rm SSHRD/usr/bin/img4tool")
os.system("rm SSHRD/usr/bin/img4")
os.system("rm SSHRD/usr/sbin/dietappleh13camerad")
os.system("rm SSHRD/usr/sbin/dietappleh16camerad")
os.system("rm SSHRD/usr/local/bin/wget")
os.system("rm SSHRD/usr/local/bin/procexp")
# Fix sftp-server not working
os.system(f"../tools/ldid_macosx_arm64 -Ssftp_server_ents.plist -M -Cadhoc SSHRD/usr/libexec/sftp-server")
os.system("sudo -A hdiutil detach -force SSHRD")
os.system("sudo -A hdiutil resize -sectors min ramdisk1.dmg")
# sign
os.system("pyimg4 im4p create -i ramdisk1.dmg -o ramdisk1.dmg.im4p -f rdsk")
os.system("pyimg4 img4 create -p ramdisk1.dmg.im4p -o Ramdisk/RestoreRamdisk.img4 -m t8030_apticket.der")

# DeviceTree
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/DeviceTree.d421ap.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/DeviceTree.d421ap.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/DeviceTree.d421ap.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/DeviceTree.d421ap.im4p.bak -o DeviceTree.raw")
os.system("./dt_patch.py DeviceTree.raw -o DeviceTree_patched.raw")
os.system("../tools/img4tool -c DeviceTree.im4p -t dtre DeviceTree_patched.raw")
os.system("../tools/img4 -i DeviceTree.im4p -o Ramdisk/DeviceTree.img4 -M t8030_apticket.der -T rdtr")

# SEP
# if not os.path.exists("270b1/sep-firmware.d421.RELEASE.im4p.bak"):
#     os.system("cp 270b1/sep-firmware.d421.RELEASE.im4p 270b1/sep-firmware.d421.RELEASE.im4p.bak")
# os.system("../tools/img4 -i 270b1/sep-firmware.d421.RELEASE.im4p.bak -o Ramdisk/SEP.img4 -M t8030_apticket.der -T rsep")
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p.bak -o Ramdisk/SEP.img4 -M t8030_apticket.der -T rsep")

# Kernelcache
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/kernelcache.release.iphone12.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/kernelcache.release.iphone12 iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/kernelcache.release.iphone12.bak")
os.system("pyimg4 im4p extract -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/kernelcache.release.iphone12.bak -o kcache.raw")
# patch 
fp = open("kcache.raw", "r+b")
# ========= seprmvr64e? =========
patch(0x20f445c, 0xD2800000)    #FFFFFFF0090F845C - ACMKernelUtils::isSEPAvailable; mov x0, #0
patch(0x217a09c, 0xD2800000)    #FFFFFFF00917E09C - AppleSEPPanicBuffer::isPanicked; mov x0, #0
patch(0x217a0a0, 0xd65f03c0)    #FFFFFFF00917E0A0 - AppleSEPPanicBuffer::isPanicked; ret
patch(0x216c214, 0xD2800000)    #FFFFFFF009170214 - AppleSEPManager::start; mov x0, #0
patch(0x216c218, 0xd65f03c0)    #FFFFFFF009170218 - AppleSEPManager::start; ret
# ========= Bypass SSV =========
# _apfs_vfsop_mount: Prevent panic "Failed to find the root snapshot. Rooting from the live fs ..."
patch(0x303f49c, 0xd503201f)    #FFFFFFF00A04349C
# _authapfs_seal_is_broken: Prevent panic "root volume seal is broken ..."
patch(0x2fae32c, 0xd503201f) #FFFFFFF009FB232C 
# _bsd_init: Prevent panic "rootvp not authenticated after mounting ..."
patch(0x36c1f48, 0xd503201f)    #FFFFFFF00A6C5F48
#__Z30_proc_check_launch_constraintsP4prociiPvmP22launch_constraint_dataPPcPm
patch(0x1f23808, 0x52800000) 
patch(0x1f23808+4, 0xd65f03c0) 
#_PE_i_can_has_debugger
patch(0x3a07368, 0xd2800020)
patch(0x3a07368+4, 0xd65f03c0)
# __ZL14postValidationP8LazyPathP7cs_blobjP12OSDictionaryhbjPKcPPcPm
patch(0x1f2b368, 0x6B00001F) 
# __ZL27_check_dyld_policy_internalP4procyPy
patch(0x1f2b8c8, 0x52800020) 
patch(0x1f2b8d4, 0x52800020) 
# __Z24AMFIIsCDHashInTrustCachehPKhPy
patch(0x1f1ebe0, 0xD503245F) # BTI c
patch(0x1f1ebe0+4, 0xD2800020)        # MOV             X0, #1
patch(0x1f1ebe0+8, 0xB4000043)      # cbz x3, #8
patch(0x1f1ebe0+12, 0xF9000060)      # STR             X0, [X3]
patch(0x1f1ebe0+16, 0xD65F03C0)     # RET
# prevent panic "unencrypted data volume is not allowed ..."
patch(0x30408ac, 0xd503201f)

fp.close()

#create im4p
os.system("pyimg4 im4p create -i kcache.raw -o krnl.im4p -d KernelManagement_host-511 -f rkrn --lzfse")

# preserve payp structure
kernel_im4p_data = Path('iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/kernelcache.release.iphone12.bak').read_bytes()
payp_offset = kernel_im4p_data.rfind(b'PAYP')
if payp_offset == -1:
    print("Couldn't find payp structure !!!")
    sys.exit()

with open('krnl.im4p', 'ab') as f:
    f.write(kernel_im4p_data[(payp_offset-10):])

payp_sz = len(kernel_im4p_data[(payp_offset-10):])
print(f"payp sz: {payp_sz}")

kernel_im4p_data = bytearray(open('krnl.im4p', 'rb').read())
kernel_im4p_data[2:6] = (int.from_bytes(kernel_im4p_data[2:6], 'big') + payp_sz).to_bytes(4, 'big')
open('krnl.im4p', 'wb').write(kernel_im4p_data)

# sign
os.system("pyimg4 img4 create -p krnl.im4p -o Ramdisk/Kernelcache.img4 -m t8030_apticket.der")

# clean
os.system("rm TXM.im4p")
os.system("rm TXM.raw")
os.system("rm SPTM.img4")
os.system("rm RestoreTrustCache.img4")
os.system("rm RestoreLogo.raw")
os.system("rm RestoreLogo.im4p")
os.system("rm PMP.img4")
os.system("rm krnl.im4p")
# os.system("rm kcache.raw")
os.system("rm ISP.img4")
os.system("rm iBEC.raw")
os.system("rm iBEC.im4p")
os.system("rm GXF.img4")
os.system("rm AVE.raw")
os.system("rm AVE.im4p")
os.system("rm AOP.im4p")
os.system("rm AOP.raw")
os.system("rm ANE.im4p")
os.system("rm ANE.raw")
os.system("rm -rf ramdisk.dmg")
os.system("rm -rf ramdisk1.dmg")
os.system("rm -rf ramdisk1.dmg.im4p")
os.system("rm -rf DeviceTree.im4p")
os.system("rm -rf SSHRD")