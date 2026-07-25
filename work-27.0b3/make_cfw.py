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

if not os.path.exists("Ramdisk"):
    os.system("mkdir Ramdisk")

if not os.path.exists("CFW"):
    os.system("cp -rf iPhone12,3,iPhone12,5_27.0_24A5380h_Restore CFW")

# Patch iBSS 
if not os.path.exists("CFW/Firmware/dfu/iBSS.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/dfu/iBSS.d421.RELEASE.im4p CFW/Firmware/dfu/iBSS.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/dfu/iBSS.d421.RELEASE.im4p -o Ramdisk/iBSS.raw")
fp = open("Ramdisk/iBSS.raw", "r+b")
# patch image4_validate_property_callback # find func's epilogue by xref "Unknown ASN1 type %llu\n"
patch(0x23EFC, 0xd503201f)      # nop
patch(0x23F00, 0xd2800000)      # mov x0, #0
# patch boot-args with "rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2B0F4, 0x90000542)      # adrp x2, #0xa8000
patch(0x2B0F8, 0x91258042)      # add x2, x2, #0x960
patch(0xD3960, "-v wdt=-1 rd=md0 -restore\x00")  # for ramdisk boot
fp.close()

# Patch iBEC
if not os.path.exists("CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak -o iBEC.raw")
fp = open("iBEC.raw", "r+b")
# patch image4_validate_property_callback
patch(0x23EFC, 0xd503201f)      # nop
patch(0x23F00, 0xd2800000)      # mov x0, #0
# patch boot-args with "rd=md0 rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2B0F4, 0x90000542)      # adrp x2, #0xa8000
patch(0x2B0F8, 0x91258042)      # add x2, x2, #0x960
patch(0xD3960, "-v wdt=-1 rd=md0 -restore\x00")  # for ramdisk boot
fp.close()
os.system("../tools/img4tool -c CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p -t ibec iBEC.raw")

# DeviceTree 
if not os.path.exists("CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/DeviceTree.d421ap.im4p CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak -o DeviceTree.raw")
# prevent data encryption for /private/var(/dev/disk1s2) and /private/var/mobile(/dev/disk1s8) # Disable "content-protect" in devicetree 
# also taken patches "no-effaceable-storage", "boot-ios-diagnostics" from https://github.com/TrungNguyen1909/qemu-t8030/blob/iOS16/hw/arm/xnu.c
os.system("./patch_dt.py DeviceTree.raw -o DeviceTree_patched.raw")
os.system("../tools/img4tool -c CFW/Firmware/all_flash/DeviceTree.d421ap.im4p -t dtre DeviceTree_patched.raw")


# RestoreRamdisk
os.system("rm -rf CFW_RD")
os.system("mkdir CFW_RD")
if not os.path.exists("CFW/094-13753-150.dmg.bak"):
    os.system("cp CFW/094-13753-150.dmg CFW/094-13753-150.dmg.bak")
os.system("pyimg4 im4p extract -i CFW/094-13753-150.dmg.bak -o ramdisk.dmg")
os.system("sudo hdiutil attach -mountpoint CFW_RD ramdisk.dmg -owners off")
# sys.stdin.read(1)
# patch restored_external
fp = open("CFW_RD/usr/local/bin/restored_external", "r+b") 
# patch "force fdr step to always succeed." xref "RestoredFDRRecover" - https://github.com/mineek/seprmvr64/tree/v2
patch(0x7e558, 0xd2800000)      # mov x0, #0
# patch _ramrod_device_has_sep
# patch(0x543F4  , 0xd2800000)      # mov x0, #0  # XXXXXXXXXXXXXX THIS IS THE PROBLEM STUCK
# patch(0x543F4+4, 0xd65f03c0)      # ret       # XXXXXXXXXXXXXX THIS IS THE PROBLEM STUCK
fp.close()
# sign
os.system("../tools/ldid_macosx_arm64 -S -M -Cadhoc CFW_RD/usr/local/bin/restored_external")
# patch /usr/sbin/asr
fp = open("CFW_RD/usr/sbin/asr", "r+b")
# patch "Image failed signature verification." ...
patch(0x1f650, 0xd503201f)      # nop
fp.close()
# sign
os.system("../tools/ldid_macosx_arm64 -S -M -Cadhoc CFW_RD/usr/sbin/asr")
os.system("sudo hdiutil detach -force CFW_RD")
os.system("pyimg4 im4p create -i ramdisk.dmg -o CFW/094-13753-150.dmg -f rdsk")


# TXM 
if not os.path.exists("CFW/Firmware/txm.iphoneos.release.im4p.bak"):
    os.system("cp CFW/Firmware/txm.iphoneos.release.im4p CFW/Firmware/txm.iphoneos.release.im4p.bak")
os.system("pyimg4 im4p extract -i CFW/Firmware/txm.iphoneos.release.im4p.bak -o TXM.raw")
# patch 
fp = open("TXM.raw", "r+b")
# Patch TXM for make running binary which is not registered in trustcache
# TXM [Error]: CodeSignature: selector: 24 | 0xA8 | 0x30 | 1
patch(0x39fa4, 0xd2800000)      # memcmp in _queryModule2
patch(0x39ca8, 0xd2800000)      # memcmp in _queryModule0
patch(0x39e10, 0xd2800000)      # memcmp in _queryModule1
# TXM [Error]: CodeSignature: selector: 24 | 0xA1 | 0x30 | 1
patch(0x3f510, 0xd503201f)          # instr in _validateConstraintsSignatureType
patch(0x3f518, 0xd503201f)          # instr in _validateConstraintsSignatureType
fp.close()
#create im4p
os.system("pyimg4 im4p create -i TXM.raw -o TXM.im4p -d 1 -f trxm --lzfse")
# preserve payp structure
txm_im4p_data = Path('CFW/Firmware/txm.iphoneos.release.im4p.bak').read_bytes()
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
os.system("mv TXM.im4p CFW/Firmware/txm.iphoneos.release.im4p")



# Kernelcache
if not os.path.exists("CFW/kernelcache.release.iphone12.bak"):
    os.system("cp CFW/kernelcache.release.iphone12 CFW/kernelcache.release.iphone12.bak")
os.system("pyimg4 im4p extract -i CFW/kernelcache.release.iphone12.bak -o kcache.raw")
fp = open("kcache.raw", "r+b")
# Rename kernel name
patch(0x3eee4, "/PATCHED_ARM64_T8030")
patch(0x3ef50, "/PATCHED_ARM64_T8030")
# ========= Bypass SSV =========
# _apfs_vfsop_mount: Prevent panic "Failed to find the root snapshot. Rooting from the live fs ..."
patch(0x303fcdc, 0xd503201f)
# _authapfs_seal_is_broken: Prevent panic "root volume seal is broken ..."
patch(0x2fae494, 0xd503201f)
# _bsd_init: Prevent panic "rootvp not authenticated after mounting ..."
patch(0x36be974, 0xd503201f)  
#__Z30_proc_check_launch_constraintsP4prociiPvmP22launch_constraint_dataPPcPm
patch(0x1f21920, 0x52800000) 
patch(0x1f21920+4, 0xd65f03c0) 
#_PE_i_can_has_debugger
patch(0x3a05230, 0xd2800020)
patch(0x3a05230+4, 0xd65f03c0)
# __ZL14postValidationP8LazyPathP7cs_blobjP12OSDictionaryhbjPKcPPcPm
patch(0x1f29480, 0x6B00001F) 
# __ZL27_check_dyld_policy_internalP4procyPy
patch(0x1f299e0, 0x52800020) 
patch(0x1f299ec, 0x52800020) 
# __Z24AMFIIsCDHashInTrustCachehPKhPy
patch(0x1f1ccf8+0, 0xD503245F)          # BTI c
patch(0x1f1ccf8+4, 0xD2800020)          # MOV             X0, #1
patch(0x1f1ccf8+8, 0xB4000043)          # cbz x3, #8
patch(0x1f1ccf8+12, 0xF9000060)         # STR             X0, [X3]
patch(0x1f1ccf8+16, 0xD65F03C0)         # RET
# ========= seprmvr64e? =========
# prevent panic "unencrypted data volume is not allowed ..."
patch(0x30410ec, 0xd503201f)

fp.close()

#create im4p
os.system("pyimg4 im4p create -i kcache.raw -o krnl.im4p -d KernelManagement_host-511 -f rkrn --lzfse")

# preserve payp structure
kernel_im4p_data = Path('CFW/kernelcache.release.iphone12.bak').read_bytes()
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
os.system("mv krnl.im4p CFW/kernelcache.release.iphone12")

# clean
os.system("rm iBEC.raw ramdisk.dmg TXM.raw kcache.raw DeviceTree_patched.raw")