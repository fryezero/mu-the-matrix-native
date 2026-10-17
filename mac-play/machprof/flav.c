#include <mach/mach.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
int main(int argc,char**argv){int pid=atoi(argv[1]);unsigned want=atoi(argv[2]);task_t task;if(task_for_pid(mach_task_self(),pid,&task))return 1;
thread_act_array_t th;mach_msg_type_number_t n;task_threads(task,&th,&n);thread_t t=th[want];
int fl[]={1,4,7,10,11,13,23,6,24};
for(int r=0;r<3;r++){thread_suspend(t);
for(unsigned i=0;i<sizeof fl/sizeof*fl;i++){natural_t buf[1024];mach_msg_type_number_t c=1024;kern_return_t kr=thread_get_state(t,fl[i],buf,&c);
printf("flavor %d kr=%d count=%u:",fl[i],kr,c);if(!kr)for(unsigned j=0;j<c&&j<40;j++)printf(" %x",buf[j]);printf("\n");}
thread_resume(t);usleep(3000);}
}
