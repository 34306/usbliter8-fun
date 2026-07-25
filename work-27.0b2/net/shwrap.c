#include <unistd.h>
// generic: argv[0] basename .real script run via bash. Hardcoded target passed at compile via TARGET.
int main(int argc, char** argv){
  char* nv[argc+2];
  nv[0]="bash";
  nv[1]=TARGET;
  for(int i=1;i<argc;i++) nv[i+1]=argv[i];
  nv[argc+1]=0;
  execv("/var/jb/usr/bin/bash", nv);
  return 127;
}
