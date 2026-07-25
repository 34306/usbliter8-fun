#include <CoreFoundation/CoreFoundation.h>
#include <stdio.h>
#include <stdlib.h>
typedef const struct __SCDynamicStore *SCDynamicStoreRef;
extern SCDynamicStoreRef SCDynamicStoreCreate(CFAllocatorRef, CFStringRef, void*, void*);
extern Boolean SCDynamicStoreSetValue(SCDynamicStoreRef, CFStringRef, CFPropertyListRef);
int main(int argc, char**argv){
  int port = argc>1 ? atoi(argv[1]) : 8888;
  SCDynamicStoreRef s = SCDynamicStoreCreate(NULL, CFSTR("uproxyset"), NULL, NULL);
  if(!s){ fprintf(stderr,"SCDynamicStoreCreate NULL\n"); return 1; }
  CFMutableDictionaryRef p = CFDictionaryCreateMutable(NULL,0,&kCFTypeDictionaryKeyCallBacks,&kCFTypeDictionaryValueCallBacks);
  int one=1; CFNumberRef n1=CFNumberCreate(NULL,kCFNumberIntType,&one);
  CFNumberRef np=CFNumberCreate(NULL,kCFNumberIntType,&port);
  CFStringRef host=CFSTR("127.0.0.1");
  CFDictionarySetValue(p,CFSTR("HTTPEnable"),n1);  CFDictionarySetValue(p,CFSTR("HTTPProxy"),host);  CFDictionarySetValue(p,CFSTR("HTTPPort"),np);
  CFDictionarySetValue(p,CFSTR("HTTPSEnable"),n1); CFDictionarySetValue(p,CFSTR("HTTPSProxy"),host); CFDictionarySetValue(p,CFSTR("HTTPSPort"),np);
  Boolean ok = SCDynamicStoreSetValue(s, CFSTR("State:/Network/Global/Proxies"), p);
  fprintf(stderr,"set=%d port=%d\n", ok, port);
  return ok?0:2;
}
