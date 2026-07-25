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

if not os.path.exists("CFW"):
    os.system("cp -rf iPhone12,3,iPhone12,5_27.0_24A5380h_Restore CFW")

# 1. Grab & Patch iBSS 
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
patch(0xD3960, "-v serial=3 debug=0x2014e launchd_unsecure_cache=1 wdt=-1\x00")  # for normal boot
fp.close()

# 2. Grab & Patch iBEC
# FYI, iBEC load address = 0x19c050000
if not os.path.exists("CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p -o iBEC.raw")
fp = open("iBEC.raw", "r+b")
# patch image4_validate_property_callback # find func's epilogue by xref "Unknown ASN1 type %llu\n"
patch(0x23EFC, 0xd503201f)      # nop
patch(0x23F00, 0xd2800000)      # mov x0, #0
# patch boot-args with "rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2B0F4, 0x90000542)      # adrp x2, #0xa8000
patch(0x2B0F8, 0x91258042)      # add x2, x2, #0x960
patch(0xD3960, "-v serial=3 debug=0x2014e launchd_unsecure_cache=1 wdt=-1\x00")  # for normal boot
fp.close()
os.system("../tools/img4tool -c iBEC.im4p -t ibec iBEC.raw")
os.system("../tools/img4 -i iBEC.im4p -o Ramdisk/iBEC.img4 -M t8030_apticket.der")

# 1. Grab & Patch iBSS 
if not os.path.exists("CFW/Firmware/all_flash/LLB.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/LLB.d421.RELEASE.im4p CFW/Firmware/all_flash/LLB.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/LLB.d421.RELEASE.im4p -o Ramdisk/LLB.raw")

# 2. Grab & Patch iBoot 
if not os.path.exists("CFW/Firmware/all_flash/iBoot.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/iBoot.d421.RELEASE.im4p CFW/Firmware/all_flash/iBoot.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/iBoot.d421.RELEASE.im4p -o Ramdisk/iBoot.raw")

# 3. Grab AppleLogo
if not os.path.exists("CFW/Firmware/all_flash/applelogo@3x~iphone.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/applelogo@3x~iphone.im4p CFW/Firmware/all_flash/applelogo@3x~iphone.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/applelogo@3x~iphone.im4p.bak -o Ramdisk/RestoreLogo.img4 -M t8030_apticket.der -T rlgo")

# 4. Grab Other Components...
# ANE
if not os.path.exists("CFW/Firmware/ane/h12_ane_fw_metis.im4p.bak"):
    os.system("cp CFW/Firmware/ane/h12_ane_fw_metis.im4p CFW/Firmware/ane/h12_ane_fw_metis.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/ane/h12_ane_fw_metis.im4p.bak -o Ramdisk/ANE.img4 -M t8030_apticket.der -T anef")

# AOP
if not os.path.exists("CFW/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p CFW/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/AOP/aopfw-iphone12aop.RELEASE.im4p.bak -o Ramdisk/AOP.img4 -M t8030_apticket.der -T aopf")

# AVE
if not os.path.exists("CFW/Firmware/ave/AppleAVE2FW_H12.im4p.bak"):
    os.system("cp CFW/Firmware/ave/AppleAVE2FW_H12.im4p CFW/Firmware/ave/AppleAVE2FW_H12.im4p.bak")
    os.system("../tools/img4 -i CFW/Firmware/ave/AppleAVE2FW_H12.im4p.bak -o Ramdisk/AVE.img4 -M t8030_apticket.der -T avef")

# SPTM
if not os.path.exists("CFW/Firmware/sptm.t8030.release.im4p.bak"):
    os.system("cp CFW/Firmware/sptm.t8030.release.im4p CFW/Firmware/sptm.t8030.release.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/sptm.t8030.release.im4p.bak -o Ramdisk/SPTM.img4 -M t8030_apticket.der -T sptm")

# TXM with patching
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
# TXM [Error]: selector: 38 | 42
# _allowedBeforeSecureChannelOperational returns always true
patch(0x2bcb4, 0xd2800020)        # FFFFFFF01702FCB4
patch(0x2bcb4+4, 0xd65f03c0)        # FFFFFFF01702FCB8
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

# sign
os.system("pyimg4 img4 create -p TXM.im4p -d 1 -o Ramdisk/TXM.img4 -m t8030_apticket.der")

# GFX
if not os.path.exists("CFW/Firmware/agx/armfw_g12p.im4p.bak"):
    os.system("cp CFW/Firmware/agx/armfw_g12p.im4p CFW/Firmware/agx/armfw_g12p.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/agx/armfw_g12p.im4p.bak -o Ramdisk/GFX.img4 -M t8030_apticket.der -T gfxf")

# ISP
if not os.path.exists("CFW/Firmware/isp_bni/adc-zelus-d4x.im4p.bak"):
    os.system("cp CFW/Firmware/isp_bni/adc-zelus-d4x.im4p CFW/Firmware/isp_bni/adc-zelus-d4x.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/isp_bni/adc-zelus-d4x.im4p.bak -o Ramdisk/ISP.img4 -M t8030_apticket.der -T ispf")

# PMP
if not os.path.exists("CFW/Firmware/pmp/t8030pmp.im4p.bak"):
    os.system("cp CFW/Firmware/pmp/t8030pmp.im4p CFW/Firmware/pmp/t8030pmp.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/pmp/t8030pmp.im4p.bak -o Ramdisk/PMP.img4 -M t8030_apticket.der -T pmpf")

# RestoreTrustCache
if not os.path.exists("CFW/Firmware/094-13753-132.dmg.trustcache.bak"):
    os.system("cp CFW/Firmware/094-13753-132.dmg.trustcache CFW/Firmware/094-13753-132.dmg.trustcache.bak")
os.system("../tools/img4 -i CFW/Firmware/094-13753-132.dmg.trustcache.bak -o Ramdisk/RestoreTrustCache.img4 -M t8030_apticket.der -T rtsc")

# SIO
if not os.path.exists("CFW/Firmware/SmartIOFirmware_ASCv2.im4p.bak"):
    os.system("cp CFW/Firmware/SmartIOFirmware_ASCv2.im4p CFW/Firmware/SmartIOFirmware_ASCv2.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/SmartIOFirmware_ASCv2.im4p.bak -o Ramdisk/SIO.img4 -M t8030_apticket.der -T siof")

# WCH
if not os.path.exists("CFW/Firmware/WirelessPower/WirelessPower.iphone12.im4p.bak"):
    os.system("cp CFW/Firmware/WirelessPower/WirelessPower.iphone12.im4p CFW/Firmware/WirelessPower/WirelessPower.iphone12.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/WirelessPower/WirelessPower.iphone12.im4p.bak -o Ramdisk/WCH.img4 -M t8030_apticket.der -T wchf")


# DeviceTree
if not os.path.exists("CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/DeviceTree.d421ap.im4p CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak -o DeviceTree.raw")
os.system("./patch_dt2.py DeviceTree.raw -o DeviceTree_patched.raw")
os.system("../tools/img4tool -c DeviceTree.im4p -t dtre DeviceTree_patched.raw")
os.system("../tools/img4 -i DeviceTree.im4p -o Ramdisk/DeviceTree.img4 -M t8030_apticket.der -T rdtr")

# SEP
if not os.path.exists("CFW/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p CFW/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/sep-firmware.d421.RELEASE.im4p.bak -o Ramdisk/SEP.img4 -M t8030_apticket.der -T rsep")

# Kernelcache
if not os.path.exists("CFW/kernelcache.release.iphone12.bak"):
    os.system("cp CFW/kernelcache.release.iphone12 CFW/kernelcache.release.iphone12.bak")
os.system("pyimg4 im4p extract -i CFW/kernelcache.release.iphone12.bak -o kcache.raw")
# patch 
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
# panic(cpu 0 caller 0xfffffff0506be614): SEP Panic: : SEPD/SEPD: 0x100010c0e 0x00057800 0x000577e4 0x100001d58 0x100001408 0x100008708 0x100000b24 0x100000ad0 0x1000012a0 [hggghgsgu]
patch(0x216fde4, 0xd2800000) #mov x0,#0 # __ZN15AppleSEPManager13sepPanicCheckEv
patch(0x216fde4+4, 0xD65F03C0) # ret
# panic(cpu 2 caller 0xfffffff044971788): SEP/OS failed to boot at stage 32
patch(0x216c658, 0xd2800000) #mov x0,#0 # __ZN15AppleSEPManager11_didTimeoutEP18IOTimerEventSource
patch(0x216c658+4, 0xD65F03C0) # ret
# fix stuck at "creating class d key for /mnt2" in restored_external when restore / fix stuck initializing keybagd when normal boot
patch(0x211a970, 0xd503201f)    # nop # __ZN23AppleKeyStoreUserClient5startEP9IOService XXX TODO SKIP
# "AppleSEPKeyStore":pid:19,:13899: operation failed (sel: 0 ret: e00002d8) -> make always successful result
patch(0x2125a40, 0xd2800000)    # mov x0, #0   # __ZN23AppleKeyStoreUserClient14externalMethodEjP25IOExternalMethodArgumentsP24IOExternalMethodDispatchP8OSObjectPv
patch(0x2125a40+4, 0xD65F03C0)      # ret
# Stop spamming log "AppleSEPKeyStore":pid:196,:13108: operation failed (sel: 7 ret: e00002d8) #"%s:%spid:%d,%s:%s%s%s%s%s%u:%s operation %s(sel: %d ret: %x%s)%s"
patch(0x2125c78, 0xd503201f)    # nop  # patched call IOLog instruction         # __ZN23AppleKeyStoreUserClient14externalMethodEjP25IOExternalMethodArgumentsP24IOExternalMethodDispatchP8OSObjectPv
# panic(cpu 0 caller 0xfffffff043769a54): "REQUIRE fail: nullptr != xartSEPSlaveEP() @ IOReturn AppleSEPManager::_powerChangeNotificat...
patch(0x216cfdc, 0xd2800000)    # mov x0, #0    # __ZN15AppleSEPManager31_powerChangeNotificationHandlerEPvjP9IOServiceS0_m
patch(0x216cfdc+4, 0xD65F03C0)  # ret
# panic(cpu 1 caller 0xfffffff03d7ce9f0): "REQUIRE fail: nullptr != hiloEP() @ IOReturn AppleSEPManager::_setPowerState(unsigned long *):2806:/Library/Caches/com.apple.xbs/E25C9853-8550-4872-8900-5C7B9C4A274F/TemporaryDirectory.L402MA/Sources/AppleSEPManager/AppleSEPMana6
patch(0x2170c78, 0xd503201f)  # nop     # __ZN15AppleSEPManager14_setPowerStateEPm
patch(0x216fc3c, 0xd503201f)  # nop     # __ZN15AppleSEPManager20_notifyOSActiveGatedEv
# patch panic
'''
IOService *AppleSEPManager::_getServiceFromEndpointName(uint32_t, uint32_t): Timed out waiting 15000000000 ns for endpoint 0x68696c6f
IOService *AppleSEPManager::_getServiceFromEndpointName(uint32_t, uint32_t): Timed out waiting 15000000000 ns for endpoint 0x7861726d
System Watchdog disabled in panic flow
AppleSMC detected kPanicBegin
panic(cpu 1 caller 0xfffffff03e6ca9c4): "REQUIRE fail: nullptr != xartSEPMasterEP() @ IOReturn AppleSEPManager::_setPowerState(unsigned long *):2816:/Library/Caches/com.apple.xbs/E25C9853-8550-4872-8900-5C7B9C4A274F/TemporaryDirectory.L402MA/Sources/AppleSEPManager/App6
Debugger message: panic
Memory ID: 0x1
'''
patch(0x2170ca8, 0xd503201f)    # nop   # __ZN15AppleSEPManager14_setPowerStateEPm
patch(0x2171230, 0xd503201f)    # nop   # xref str "AppleSEP:WARNING: Unable to reseed XNU PRNG, attempt %d/%d\n"

# TODO PATCH
'''
virtual void AppleSEPManager::systemWillShutdown(IOOptionBits): Received system will shut down notification
AppleSEP:WARNING: attempt to send message to SEP in non-receptive state 5
AppleSEP:WARNING: _cmsgSend: send failed: result 0xe00002d8 opcode 12 endpoint 0 tag 8
System Watchdog disabled in panic flow
AppleSMC detected kPanicBegin
panic(cpu 1 caller 0xfffffff052ecb41c): "REQUIRE fail: result == kIOReturnSuccess || result == kIOReturnBadArgument @ virtual void AppleSEPManager::systemWillShutdown(IOOptionBits):4313:/Library/Caches/com.apple.xbs/E25C9853-8550-4872-8900-5C7B9C4A274F/TemporaryDirecto3
'''


'''
busy timeout[0], (60s): multiple entries holding the registry busy, IOKit termination queue depth 212: 'RootDomainUserClient' (1,2001), 'ApplePPMUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001), 'ApplePMGRUserClient' (1System Watchdow
AppleSMC detected kPanicBegin
panic(cpu 2 caller 0xfffffff054e8afdc): busy timeout[0], (60s): multiple entries holding the registry busy, IOKit termination queue depth 212: 'RootDomainUserClient' (1,2001), 'ApplePPMUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001)0
'''
# COULDN"T FIND SOLUTION. TEMP FIX: wdt=-1 
# AppleSEP:WARNING: _cmsgSend: send failed: result 0xe00002d8 opcode 0 endpoint 0 tag 8
# patch(0x2163d2c, 0x52800000)            # __ZN15AppleSEPControl9_cmsgSendEP15AppleSEPMessagePjPb
# patch(0x2163d2c+4, 0xd65f03c0)            
# patch all ret 0 functions xref string "/Library/Caches/com.apple.xbs/24D40BA6-0B53-409C-8EE1-C0DB6633914A/TemporaryDirectory.KzFAA2/Sources/AppleCredentialManager/AppleCredentialManager/AppleCredentialManager.cpp"
RET_VAL = 0x52800000   # mov w0, #0   (set to 0x52800020 for mov w0,#1 / return 1)
RET     = 0xd65f03c0   # ret
# patch(0x20f4e74,   RET_VAL)   # func @ va 0xfffffff0090f8e74 # just one patch make bootable ENOUGH??
# patch(0x20f4e74+4, RET)
# patch(0x20fbcb0,   RET_VAL)   # func @ va 0xfffffff0090ffcb0  just one patch make bootable ENOUGH??
# patch(0x20fbcb0+4, RET)
# patch(0x20f5334,   RET_VAL)   # func @ va 0xfffffff0090f9334  # __ZN22AppleCredentialManager9startImplEP9IOService
# patch(0x20f5334+4, RET)

# prevent stuck at AppleCredentialManager: waitForSEPEndpointOutsideACMCommandGate: waiting cmd=51.
# patch(0x20f44e4, RET)    # __ZN14ACMKernelUtils18waitForSEPEndpointEv    # ret


patch(0x20f4e84,   RET_VAL)     # __ZN22AppleCredentialManager34sepManagerMatchedThreadCallHandlerEv
patch(0x20f4e84+4, RET)

patch(0x20f554c,   RET_VAL)     # __ZN22AppleCredentialManager20callPlatformFunctionEPK8OSSymbolbPvS3_S3_S3_
patch(0x20f554c+4, RET)
patch(0x20f55d0,   RET_VAL)     # cmdContextV2
patch(0x20f55d0+4, RET)
patch(0x20f5658,   RET_VAL)     # cmdContextV3
patch(0x20f5658+4, RET)

patch(0x20f5870,   RET_VAL)     # performCommandGated
patch(0x20f5870+4, RET)
patch(0x20f63a4,   RET_VAL)     # _performKernelControl
patch(0x20f63a4+4, RET)
patch(0x20f6760,   RET_VAL)     # _performCommand
patch(0x20f6760+4, RET)
patch(0x20f6988,   RET_VAL)     # processSCRDResponsePayload
patch(0x20f6988+4, RET)
patch(0x20f6bb4,   RET_VAL)     # scheduleDblClickDeferredAck
patch(0x20f6bb4+4, RET)
patch(0x20f6cd4,   RET_VAL)     # updateAnalytics
patch(0x20f6cd4+4, RET)
patch(0x20f6e38,   RET_VAL)     # performSCRDInitialization
patch(0x20f6e38+4, RET)

patch(0x20f70fc,   RET_VAL)     # sendSEPCommand
patch(0x20f70fc+4, RET)
patch(0x20f7aac,   RET_VAL)     # __ZN22AppleCredentialManager19_setPropertiesGatedEP8OSObject
patch(0x20f7aac+4, RET)
patch(0x20f7f34,   RET_VAL)     # __ZN22AppleCredentialManager28performDoubleClickQueryGatedEPy
patch(0x20f7f34+4, RET)
patch(0x20f8024,   RET_VAL)     # __ZN22AppleCredentialManager29performLoggingLevelQueryGatedEPy
patch(0x20f8024+4, RET)
patch(0x20f81f0,   RET_VAL)     # lockItem
patch(0x20f81f0+4, RET)
patch(0x20f841c,   RET_VAL)     # unlockItem
patch(0x20f841c+4, RET)
patch(0x20f88d0,   RET_VAL)     # handleSEPMessage
patch(0x20f88d0+4, RET)
patch(0x20f8bb8,   RET_VAL)     # __ZN20AppleRepairSEPDriver17readFromSEPBufferEPvm
patch(0x20f8bb8+4, RET)

patch(0x20f8d18,   RET_VAL)     # writeToSEPBuffer
patch(0x20f8d18+4, RET)
patch(0x20f90c0,   RET_VAL)     # sendSEPMessage
patch(0x20f90c0+4, RET)
patch(0x20f92f8,   RET_VAL)     # __ZN22AppleCredentialManager14clearSEPBufferEP13IOSlaveMemorym
patch(0x20f92f8+4, RET)
patch(0x20f9494,   RET_VAL)     # getSEPEndpoint
patch(0x20f9494+4, RET)
patch(0x20fa0d4,   RET_VAL)     # powerOffActionGated
patch(0x20fa0d4+4, RET)
patch(0x20fa388,   RET_VAL)     # sepManagerMatchedGated
patch(0x20fa388+4, RET)
patch(0x21066b0,   RET_VAL)     # setPowerStateGated
patch(0x21066b0+4, RET)


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

# sign
os.system("pyimg4 img4 create -p krnl.im4p -o Ramdisk/Kernelcache.img4 -m t8030_apticket.der")



# NOTE: About sep boot fail?
# init_data_protection: can't open '/private/preboot/59A79B92174AC2C86D2186C59241328966B7BEF699FEB41644661A479A509074D5EBDBDD27B5A0EBCB3805EFDF6EEA7E/usr/standalone/firmware/sep-firmware.img4', errno: No such file or directory(2)
# ramdisk 로 부팅해서 내장된 apticket.der을 가져온다.
# 그걸로 서명한 sep-firmware을 가져다놓는다. 끝?


# clean
os.system("rm TXM.im4p")
os.system("rm TXM.raw")
os.system("rm SPTM.img4")
os.system("rm RestoreTrustCache.img4")
os.system("rm RestoreLogo.raw")
os.system("rm RestoreLogo.im4p")
os.system("rm PMP.img4")
os.system("rm krnl.im4p")
os.system("rm kcache.raw")
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