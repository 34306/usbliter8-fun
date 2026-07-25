#include <spawn.h>
#include <unistd.h>
#include <stdlib.h>
#include <fcntl.h>
extern char **environ;
extern int posix_spawnattr_setprocesstype_np(posix_spawnattr_t*, int);
#ifndef POSIX_SPAWN_SETSID
#define POSIX_SPAWN_SETSID 0x0400
#endif
#define POSIX_SPAWN_PROC_TYPE_APP_DEFAULT 0x00000001
int main(void){
  posix_spawnattr_t a; posix_spawnattr_init(&a);
  posix_spawnattr_setflags(&a, POSIX_SPAWN_SETSID);
  posix_spawnattr_setprocesstype_np(&a, POSIX_SPAWN_PROC_TYPE_APP_DEFAULT);
  posix_spawn_file_actions_t fa; posix_spawn_file_actions_init(&fa);
  posix_spawn_file_actions_addopen(&fa,0,"/dev/null",O_RDONLY,0);
  posix_spawn_file_actions_addopen(&fa,1,"/tmp/tvnc.log",O_WRONLY|O_CREAT|O_APPEND,0644);
  posix_spawn_file_actions_adddup2(&fa,1,2);
  setenv("TROLLVNC_PASSWORD","alpine",1);
  setenv("DISABLE_TWEAKS","1",1);
  char *av[]={"/var/jb/usr/bin/trollvncserver",0};
  pid_t pid; int r=posix_spawn(&pid,av[0],&fa,&a,av,environ);
  return r;
}
