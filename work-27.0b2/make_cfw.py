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
    os.system("cp -rf iPhone12,3,iPhone12,5_27.0_24A5370h_Restore CFW")

# Patch iBSS 
if not os.path.exists("iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p.bak"):
    os.system("cp iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i iPhone12,3,iPhone12,5_27.0_24A5370h_Restore/Firmware/dfu/iBSS.d421.RELEASE.im4p -o Ramdisk/iBSS.raw")
fp = open("Ramdisk/iBSS.raw", "r+b")
# Notice if loaded PATCHED iBSS (optional)
# patch(0x2C0, "PATCHED")
# patch(0x13CAD1, "PATCHED_1")
# patch image4_validate_property_callback
patch(0x23DB0, 0xd503201f)      # nop
patch(0x23DB4, 0xd2800000)      # mov x0, #0
# patch boot-args with "rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2AFBC, 0xB0000542)      # adrp x2, #0xa9000
patch(0x2AFC0, 0x91214042)      # add x2, x2, #0x850
patch(0xD3850, "-v wdt=-1 rd=md0 -restore\x00")  # for ramdisk boot
fp.close()

# Patch iBEC
# FYI, iBEC load address = 0x19c050000
if not os.path.exists("CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak"):
    os.system("cp CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p.bak -o iBEC.raw")
fp = open("iBEC.raw", "r+b")
# Notice if loaded PATCHED iBEC (optional)
# patch(0x2C0, "PATCHED")
# patch(0x13CAD1, "PATCHED_2")
# Keep nonce
patch(0x36bd0, 0x1400000a)      # b #0x28
# patch image4_validate_property_callback
patch(0x23DB0, 0xd503201f)      # nop
patch(0x23DB4, 0xd2800000)      # mov x0, #0
# patch boot-args with "rd=md0 rd=md0 serial=3 debug=0x2014e -v wdt=-1 %s"
patch(0x2AFBC, 0xB0000542)      # adrp x2, #0xa9000
patch(0x2AFC0, 0x91214042)      # add x2, x2, #0x850
patch(0xD3850, "-v wdt=-1 rd=md0 -restore\x00")  # bootargs 
fp.close()
os.system("../tools/img4tool -c CFW/Firmware/dfu/iBEC.d421.RELEASE.im4p -t ibec iBEC.raw")

# DeviceTree 
if not os.path.exists("CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak"):
    os.system("cp CFW/Firmware/all_flash/DeviceTree.d421ap.im4p CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak")
os.system("../tools/img4 -i CFW/Firmware/all_flash/DeviceTree.d421ap.im4p.bak -o DeviceTree.raw")
# prevent data encryption for /private/var(/dev/disk1s2) and /private/var/mobile(/dev/disk1s8) # Disable "content-protect" in devicetree 
os.system("./dt_patch2.py DeviceTree.raw -o DeviceTree_patched.raw")
os.system("../tools/img4tool -c CFW/Firmware/all_flash/DeviceTree.d421ap.im4p -t dtre DeviceTree_patched.raw")



# RestoreRamdisk
os.system("rm -rf CFW_RD")
os.system("mkdir CFW_RD")
if not os.path.exists("CFW/094-13753-132.dmg.bak"):
    os.system("cp CFW/094-13753-132.dmg CFW/094-13753-132.dmg.bak")
os.system("pyimg4 im4p extract -i CFW/094-13753-132.dmg.bak -o ramdisk.dmg")
os.system("sudo -A hdiutil attach -mountpoint CFW_RD ramdisk.dmg -owners off")
# sys.stdin.read(1)
# patch restored_external
fp = open("CFW_RD/usr/local/bin/restored_external", "r+b") 
# patch "force fdr step to always succeed." xref "RestoredFDRRecover" - https://github.com/mineek/seprmvr64/tree/v2
patch(0x7e53c, 0xd2800000)      # mov x0, #0
# # patch _ramrod_device_has_sep
# patch(0x543E4, 0xd2800000)      # mov x0, #0  # XXXXXXXXXXXXXX THIS IS THE PROBLEM STUCK
# patch(0x543E4+4, 0xd65f03c0)      # ret       # XXXXXXXXXXXXXX THIS IS THE PROBLEM STUCK
# patch(0x32048, 0xd2800000)  # sub_100031FF8
# patch(0x323f0, 0xd2800000)  # sub_1000323C4
# patch(0x345fc, 0xd2800000)  # sub_100033B5C
# patch(0x544b8, 0xd2800000)  # _ramrod_init_gigalocker
# patch(0x5456c, 0xd2800000)  # _ramrod_shutdown_gigalocker
# patch(0x546b8, 0xd2800000)  # _ramrod_load_sep_os
# patch(0x54bb8, 0xd2800000)  # sub_100054B4C
# patch(0x54e4c, 0xd2800000)  # _ramrod_commit_sep_hash_with_options
# patch(0x55858, 0xd2800000)  # _ramrod_commit_sep_hash_with_options
# patch(0x561a8, 0xd2800000)  # _ramrod_kill_sep_nonce
# patch(0x58a5c, 0xd2800000)  # sub_100058948
# patch(0x58ac4, 0xd2800000)  # sub_100058948
# patch(0x59238, 0xd2800000)  # sub_100058948
# _ramrod_device_has_baseband / ramrod_device_has_baseband_legacy
patch(0x49e38, 0xd2800000)
patch(0x49e38+4, 0xD65F03C0)
patch(0x49DC0, 0xd2800000)
patch(0x49DC0+4, 0xD65F03C0)
fp.close()
# sign
os.system("../tools/ldid_macosx_arm64 -S -M -Cadhoc CFW_RD/usr/local/bin/restored_external")
# patch /usr/sbin/asr
fp = open("CFW_RD/usr/sbin/asr", "r+b")
# patch "Image failed signature verification." ...
patch(0x24d34, 0xd503201f)      # nop
fp.close()
# sign
os.system("../tools/ldid_macosx_arm64 -S -M -Cadhoc CFW_RD/usr/sbin/asr")
os.system("sudo -A hdiutil detach -force CFW_RD")
os.system("pyimg4 im4p create -i ramdisk.dmg -o CFW/094-13753-132.dmg -f rdsk")


# TXM
if not os.path.exists("CFW/Firmware/txm.iphoneos.release.im4p.bak"):
    os.system("cp CFW/Firmware/txm.iphoneos.release.im4p CFW/Firmware/txm.iphoneos.release.im4p.bak")
os.system("pyimg4 im4p extract -i CFW/Firmware/txm.iphoneos.release.im4p.bak -o TXM.raw")
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
patch(0x3ee1e, "/PATCHED_ARM64_T8030")
patch(0x3edb3, "/PATCHED_ARM64_T8030")
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


# ========= seprmvr64e? =========
# prevent panic "unencrypted data volume is not allowed ..."
patch(0x30408ac, 0xd503201f)
# apfs_is_valid_class:2496: disk1s8 rejecting class open (class 2) because we're not content protected
# patch(0x340c538, 0xd2800020)    # mov x0, #1    # 0xFFFFFFF00A410538 proc_ignores_content_protection
# patch(0x340c538+4, 0xD65F03C0)  # ret
'''
# ERROR: sensorHubDirectWriteSensorExchangeKey(2051359048) failed - i don't think this patches resolve wifi issues..
# patch(0x21945c4, 0xd2800000)  # mov x0, #0      # __ZN8AppleSMC20callPlatformFunctionEPK8OSSymbolbPvS3_S3_S3_   # make not to SET fPanicCalled_0
# patch(0x2193f54, 0xd2800000)  # mov x0, #0      # __ZN8AppleSMC37sensorHubDirectWriteSensorExchangeKeyEjP17SMCSensorEx_Jumbo
# patch(0x2193f54+4, 0xd65f03c0)  # ret           # __ZN8AppleSMC37sensorHubDirectWriteSensorExchangeKeyEjP17SMCSensorEx_Jumbo
# panic(cpu 0 caller 0xfffffff0506be614): SEP Panic: : SEPD/SEPD: 0x100010c0e 0x00057800 0x000577e4 0x100001d58 0x100001408 0x100008708 0x100000b24 0x100000ad0 0x1000012a0 [hggghgsgu]
patch(0x2170af4, 0xd2800000) #mov x0,#0 # __ZN15AppleSEPManager13sepPanicCheckEv
patch(0x2170af4+4, 0xD65F03C0) # ret
# panic(cpu 2 caller 0xfffffff044971788): SEP/OS failed to boot at stage 32
patch(0x216d380, 0xd2800000) #mov x0,#0 # __ZN15AppleSEPManager11_didTimeoutEP18IOTimerEventSource
patch(0x216d380+4, 0xD65F03C0) # ret
# fix stuck at "creating class d key for /mnt2" in restored_external when restore / fix stuck initializing keybagd when normal boot
# patch(0x211bc70, 0xd503201f)    # nop # __ZN23AppleKeyStoreUserClient5startEP9IOService
# "AppleSEPKeyStore":pid:19,:13899: operation failed (sel: 0 ret: e00002d8) -> make always successful result
patch(0x2126ce0, 0xd2800000)    # mov x0, #0   # __ZN23AppleKeyStoreUserClient14externalMethodEjP25IOExternalMethodArgumentsP24IOExternalMethodDispatchP8OSObjectPv
patch(0x2126ce0+4, 0xD65F03C0)      # ret
# Stop spamming log "AppleSEPKeyStore":pid:196,:13108: operation failed (sel: 7 ret: e00002d8) #"%s:%spid:%d,%s:%s%s%s%s%s%u:%s operation %s(sel: %d ret: %x%s)%s"
patch(0x2126f18, 0xd503201f)    # nop  # patched call IOLog instruction         # __ZN23AppleKeyStoreUserClient14externalMethodEjP25IOExternalMethodArgumentsP24IOExternalMethodDispatchP8OSObjectPv
# panic(cpu 0 caller 0xfffffff043769a54): "REQUIRE fail: nullptr != xartSEPSlaveEP() @ IOReturn AppleSEPManager::_powerChangeNotificat...
patch(0x216dd04, 0xd2800000)    # mov x0, #0    # __ZN15AppleSEPManager31_powerChangeNotificationHandlerEPvjP9IOServiceS0_m
patch(0x216dd04+4, 0xD65F03C0)  # ret

# busy timeout[0], (60s): multiple entries holding the registry busy, IOKit termination queue depth 212: 'RootDomainUserClient' (1,2001), 'ApplePPMUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001), 'ApplePMGRUserClient' (1System Watchdow
# AppleSMC detected kPanicBegin
# panic(cpu 2 caller 0xfffffff054e8afdc): busy timeout[0], (60s): multiple entries holding the registry busy, IOKit termination queue depth 212: 'RootDomainUserClient' (1,2001), 'ApplePPMUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001), 'ApplePMGRUserClient' (1,2001)0
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


patch(0x20f6228,   RET_VAL)   # func @ va 0xfffffff0090fa228  # __ZN22AppleCredentialManager34sepManagerMatchedThreadCallHandlerEv
patch(0x20f6228+4, RET)

patch(0x20f68f0,   RET_VAL)   # func @ va 0xfffffff0090fa8f0  # __ZN22AppleCredentialManager20callPlatformFunctionEPK8OSSymbolbPvS3_S3_S3_
patch(0x20f68f0+4, RET)
patch(0x20f6974,   RET_VAL)   # func @ va 0xfffffff0090fa974  # cmdContextV2
patch(0x20f6974+4, RET)
patch(0x20f69fc,   RET_VAL)   # func @ va 0xfffffff0090fa9fc  # cmdContextV3
patch(0x20f69fc+4, RET)

patch(0x20f6c14,   RET_VAL)   # func @ va 0xfffffff0090fac14  # performCommandGated
patch(0x20f6c14+4, RET)
patch(0x20f7748,   RET_VAL)   # func @ va 0xfffffff0090fb748  # _performKernelControl
patch(0x20f7748+4, RET)
patch(0x20f7b04,   RET_VAL)   # func @ va 0xfffffff0090fbb04  # _performCommand
patch(0x20f7b04+4, RET)
patch(0x20f7d2c,   RET_VAL)   # func @ va 0xfffffff0090fbd2c  # processSCRDResponsePayload
patch(0x20f7d2c+4, RET)
patch(0x20f7f58,   RET_VAL)   # func @ va 0xfffffff0090fbf58  # scheduleDblClickDeferredAck
patch(0x20f7f58+4, RET)
patch(0x20f8078,   RET_VAL)   # func @ va 0xfffffff0090fc078  # updateAnalytics
patch(0x20f8078+4, RET)
patch(0x20f81dc,   RET_VAL)   # func @ va 0xfffffff0090fc1dc  # performSCRDInitialization
patch(0x20f81dc+4, RET)

patch(0x20f84a0,   RET_VAL)   # func @ va 0xfffffff0090fc4a0  # sendSEPCommand
patch(0x20f84a0+4, RET)
patch(0x20f8e50,   RET_VAL)   # func @ va 0xfffffff0090fce50  # __ZN22AppleCredentialManager19_setPropertiesGatedEP8OSObject
patch(0x20f8e50+4, RET)
patch(0x20f92d8,   RET_VAL)   # func @ va 0xfffffff0090fd2d8  # __ZN22AppleCredentialManager28performDoubleClickQueryGatedEPy
patch(0x20f92d8+4, RET)
patch(0x20f93c9,   RET_VAL)   # func @ va 0xFFFFFFF0090FD3C8  # __ZN22AppleCredentialManager29performLoggingLevelQueryGatedEPy
patch(0x20f93c8+4, RET)
patch(0x20f9594,   RET_VAL)   # func @ va 0xfffffff0090fd594  # lockItem
patch(0x20f9594+4, RET)
patch(0x20f97c0,   RET_VAL)   # func @ va 0xfffffff0090fd7c0  # unlockItem
patch(0x20f97c0+4, RET)
patch(0x20f9c74,   RET_VAL)   # func @ va 0xfffffff0090fdc74  # handleSEPMessage
patch(0x20f9c74+4, RET)
patch(0x20f9f5c,   RET_VAL)   # func @ va 0xfffffff0090fdf5c  # __ZN20AppleRepairSEPDriver17readFromSEPBufferEPvm
patch(0x20f9f5c+4, RET)

patch(0x20fa0bc,   RET_VAL)   # func @ va 0xfffffff0090fe0bc  # writeToSEPBuffer
patch(0x20fa0bc+4, RET)
patch(0x20fa464,   RET_VAL)   # func @ va 0xfffffff0090fe464  # sendSEPMessage
patch(0x20fa464+4, RET)
patch(0x20fa69c,   RET_VAL)   # func @ va 0xfffffff0090fe69c  # __ZN22AppleCredentialManager14clearSEPBufferEP13IOSlaveMemorym
patch(0x20fa69c+4, RET)
patch(0x20fa838,   RET_VAL)   # func @ va 0xfffffff0090fe838  # getSEPEndpoint
patch(0x20fa838+4, RET)
patch(0x20fb478,   RET_VAL)   # func @ va 0xfffffff0090ff478  # powerOffActionGated
patch(0x20fb478+4, RET)
patch(0x20fb72c,   RET_VAL)   # func @ va 0xfffffff0090ff72c  # sepManagerMatchedGated
patch(0x20fb72c+4, RET)
patch(0x2107a5c,   RET_VAL)   # func @ va 0xfffffff00910ba5c    # setPowerStateGated
patch(0x2107a5c+4, RET)
'''


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