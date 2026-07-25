#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
typedef const struct __SCDynamicStore *SCDynamicStoreRef;
extern SCDynamicStoreRef SCDynamicStoreCreate(CFAllocatorRef, CFStringRef, void*, void*);
extern Boolean SCDynamicStoreSetValue(SCDynamicStoreRef, CFStringRef, CFPropertyListRef);
static CFArrayRef arr1(CFStringRef a){ return CFArrayCreate(NULL,(const void**)&a,1,&kCFTypeArrayCallBacks); }
int main(void){
  SCDynamicStoreRef s=SCDynamicStoreCreate(NULL,CFSTR("netup"),NULL,NULL);
  if(!s){fprintf(stderr,"no store\n");return 1;}
  CFStringRef svc=CFSTR("USBNET"), ifn=CFSTR("en2"), ip=CFSTR("10.7.0.2"), mask=CFSTR("255.255.255.0"), rtr=CFSTR("10.7.0.1");
  // Service IPv4
  CFMutableDictionaryRef v4=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
  CFDictionarySetValue(v4,CFSTR("Addresses"),arr1(ip));
  CFDictionarySetValue(v4,CFSTR("SubnetMasks"),arr1(mask));
  CFDictionarySetValue(v4,CFSTR("Router"),rtr);
  CFDictionarySetValue(v4,CFSTR("InterfaceName"),ifn);
  Boolean a=SCDynamicStoreSetValue(s,CFSTR("State:/Network/Service/USBNET/IPv4"),v4);
  // Service DNS
  CFStringRef dns[2]={CFSTR("8.8.8.8"),CFSTR("1.1.1.1")};
  CFArrayRef darr=CFArrayCreate(NULL,(const void**)dns,2,&kCFTypeArrayCallBacks);
  CFMutableDictionaryRef dd=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
  CFDictionarySetValue(dd,CFSTR("ServerAddresses"),darr);
  Boolean b=SCDynamicStoreSetValue(s,CFSTR("State:/Network/Service/USBNET/DNS"),dd);
  // Global IPv4 (primary)
  CFMutableDictionaryRef g=CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
  CFDictionarySetValue(g,CFSTR("PrimaryService"),svc);
  CFDictionarySetValue(g,CFSTR("PrimaryInterface"),ifn);
  CFDictionarySetValue(g,CFSTR("Router"),rtr);
  Boolean c=SCDynamicStoreSetValue(s,CFSTR("State:/Network/Global/IPv4"),g);
  // Global DNS too
  Boolean e=SCDynamicStoreSetValue(s,CFSTR("State:/Network/Global/DNS"),dd);
  fprintf(stderr,"svcIPv4=%d svcDNS=%d globalIPv4=%d globalDNS=%d\n",a,b,c,e);
  return 0;
}
